import math
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from flood_adapt.misc.log import FloodAdaptLogging

logger = FloodAdaptLogging.getLogger(__name__)


def _iter_line_geometries(geometry: shapely.Geometry):
    if geometry is None or geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        return [geometry]
    if geometry.geom_type == "MultiLineString":
        return list(geometry.geoms)
    return []


def _sampling_distances(line: shapely.LineString, interval_m: float):
    if math.isclose(line.length, 0.0):
        return [0.0]

    distances = list(np.arange(0.0, line.length, interval_m))
    if not distances or not math.isclose(distances[-1], line.length):
        distances.append(float(line.length))
    return distances


def _build_line_and_point_frames(
    gdf_metric: gpd.GeoDataFrame, interval_m: float
) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    line_records = []
    point_records = []
    line_id = 0

    cols = [c for c in gdf_metric.columns if c != "geometry"]

    for row in gdf_metric.itertuples(index=False):
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        for line in _iter_line_geometries(geom):
            for vertex_idx, dist in enumerate(_sampling_distances(line, interval_m)):
                point_records.append(
                    {
                        "line_id": line_id,
                        "vertex_idx": vertex_idx,
                        "geometry": line.interpolate(dist),
                    }
                )

            record = {c: getattr(row, c) for c in cols}
            record["line_id"] = line_id
            record["geometry"] = line
            line_records.append(record)

            line_id += 1

    return (
        gpd.GeoDataFrame(line_records, crs=gdf_metric.crs),
        gpd.GeoDataFrame(point_records, crs=gdf_metric.crs),
    )


def _to_z_linestring(
    line_points: list[shapely.Point],
    line_z: list[float],
    fallback_geometry: shapely.LineString,
    fallback_z: float,
) -> tuple[shapely.LineString, float]:
    if len(line_points) < 2 or len(line_points) != len(line_z):
        msg = "Insufficient or mismatched points and Z values for line. Returning fallback geometry and Z."
        warnings.warn(msg)
        logger.warning(msg)
        return fallback_geometry, fallback_z
    z_coords = [
        (point.x, point.y, float(z_val)) for point, z_val in zip(line_points, line_z)
    ]
    return shapely.LineString(z_coords), float(np.mean(line_z))


def _scale_z_geometry(
    geometry: shapely.Geometry, z_conversion: float
) -> shapely.Geometry:
    if geometry is None or geometry.is_empty:
        return geometry
    if geometry.geom_type == "LineString":
        coords = list(geometry.coords)
        if not coords or len(coords[0]) < 3:
            return geometry
        scaled = [(x, y, z * z_conversion) for x, y, z in coords]
        return shapely.LineString(scaled)
    if geometry.geom_type == "MultiLineString":
        lines = [_scale_z_geometry(line, z_conversion) for line in geometry.geoms]
        return shapely.MultiLineString(lines)
    return geometry


def _apply_bfe_sampling_to_points(
    gdf_points: gpd.GeoDataFrame,
    gdf_bfe: gpd.GeoDataFrame,
    bfe_field_name: str,
    elevation_offset: float,
) -> gpd.GeoDataFrame:
    gdf_join = gpd.sjoin(
        gdf_points,
        gdf_bfe[[bfe_field_name, "geometry"]],
        how="left",
        predicate="intersects",
    )
    # Ensure that each sampled point (line_id, vertex_idx) has at most one BFE value
    gdf_join = gdf_join.sort_values(["line_id", "vertex_idx"]).drop_duplicates(
        subset=["line_id", "vertex_idx"], keep="first"
    )
    sampled_bfe = pd.to_numeric(gdf_join[bfe_field_name], errors="coerce")
    gdf_join["z"] = sampled_bfe + elevation_offset

    gdf_join.loc[sampled_bfe.isna(), "z"] = elevation_offset

    return gdf_join.sort_values(["line_id", "vertex_idx"])


def create_z_linestrings_from_bfe(
    gdf_lines: gpd.GeoDataFrame,
    gdf_bfe: gpd.GeoDataFrame,
    bfe_field_name: str,
    interval_m: float = 100.0,
    elevation_offset: float = 0.0,
    z_conversion: float | None = None,
) -> gpd.GeoDataFrame:
    """
    Densify input line geometries and construct 3D LineStrings using sampled BFE values.

    The input line features are reprojected to a metric CRS, densified at a regular
    spacing of ``interval_m``, and converted to point vertices. These vertices are
    spatially joined to the provided BFE surface to sample base flood elevation
    values from ``bfe_field_name``. The sampled BFE values, plus an optional
    ``elevation_offset``, are used as Z-coordinates to build Z-enabled
    LineStrings (x, y, z). A representative elevation value per line is also
    computed and stored in the output.

    Parameters
    ----------
    gdf_lines : geopandas.GeoDataFrame
        GeoDataFrame containing the input line geometries to be densified and
        converted to Z-enabled LineStrings. Must have a valid CRS.
    gdf_bfe : geopandas.GeoDataFrame
        GeoDataFrame providing the base flood elevation (BFE) data. Must contain
        a geometry column and the attribute specified by ``bfe_field_name``,
        and should be in the same CRS as ``gdf_lines`` (or a CRS that is
        compatible with the spatial join used for sampling).
    bfe_field_name : str
        Name of the column in ``gdf_bfe`` that contains BFE values to be
        sampled and used as Z-coordinates.
    interval_m : float, optional
        Target spacing, in meters, used to densify the input lines. Must be
        strictly positive. Smaller values produce more vertices and smoother
        Z-profiles, at the cost of additional computation.
    elevation_offset : float, optional
        Constant elevation offset (in the same units as the BFE values) added
        to all sampled BFE values. This value is also used as the fallback Z
        when no BFE value can be sampled for a vertex or an entire line.
    z_conversion : float, optional
        Factor applied to all sampled Z values (including the elevation offset)
        before building Z-enabled geometries. Use this to convert heights to
        target units.

    Returns
    -------
    geopandas.GeoDataFrame
        A new GeoDataFrame containing densified, Z-enabled LineStrings as the
        geometry column and a ``"z"`` column storing a representative elevation
        per feature. The schema generally mirrors ``gdf_lines`` (minus internal
        helper columns such as ``"line_id"``), and the index is reset.

    Raises
    ------
    ValueError
        If ``interval_m`` is less than or equal to zero.
    """
    if interval_m <= 0:
        raise ValueError("interval_m must be larger than zero.")

    if gdf_lines.empty:
        return gdf_lines

    metric_crs = gdf_lines.estimate_utm_crs() or "EPSG:3857"
    gdf_metric = gdf_lines.to_crs(metric_crs)

    gdf_rows_metric, gdf_points_metric = _build_line_and_point_frames(
        gdf_metric=gdf_metric,
        interval_m=interval_m,
    )

    if gdf_rows_metric.empty or gdf_points_metric.empty:
        return gdf_lines

    gdf_rows = gdf_rows_metric.to_crs(metric_crs)
    gdf_points = gdf_points_metric.to_crs(metric_crs)
    gdf_bfe = gdf_bfe.to_crs(metric_crs)

    gdf_join = _apply_bfe_sampling_to_points(
        gdf_points=gdf_points,
        gdf_bfe=gdf_bfe,
        bfe_field_name=bfe_field_name,
        elevation_offset=elevation_offset,
    )

    z_by_line = {}
    for line_id, group in gdf_join.groupby("line_id", sort=False):
        z_geom, z_val = _to_z_linestring(
            line_points=list(group.geometry),
            line_z=list(group.z),
            fallback_geometry=None,
            fallback_z=elevation_offset,
        )
        z_by_line[line_id] = (z_geom, z_val)

    z_geometries = []
    representative_z = []

    for row in gdf_rows.itertuples(index=False):
        geom, z_val = z_by_line.get(row.line_id, (row.geometry, elevation_offset))
        z_geometries.append(geom)
        representative_z.append(z_val)

    gdf_out = gdf_rows.drop(columns=["line_id"]).copy()
    gdf_out.geometry = z_geometries
    gdf_out["z"] = representative_z

    if z_conversion is not None:
        gdf_out.geometry = gdf_out.geometry.apply(
            lambda geom: _scale_z_geometry(geom, z_conversion)
        )
        gdf_out["z"] = gdf_out["z"] * z_conversion
    return gdf_out.reset_index(drop=True)
