import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

from flood_adapt.workflows.floodwall import create_z_linestrings_from_bfe


def test_create_z_linestrings_from_bfe_densifies_and_samples():
    gdf_lines = gpd.GeoDataFrame(
        {"name": ["fw"]},
        geometry=[LineString([(0.0, 0.0), (250.0, 0.0)])],
        crs="EPSG:3857",
    )
    gdf_bfe = gpd.GeoDataFrame(
        {"bfe": [1.0, 2.0]},
        geometry=[
            Polygon([(-10, -10), (150, -10), (150, 10), (-10, 10)]),
            Polygon([(150, -10), (260, -10), (260, 10), (150, 10)]),
        ],
        crs="EPSG:3857",
    )

    gdf_out = create_z_linestrings_from_bfe(
        gdf_lines=gdf_lines,
        gdf_bfe=gdf_bfe,
        bfe_field_name="bfe",
        interval_m=100.0,
        elevation_offset=0.5,
    )

    assert len(gdf_out) == 1
    geom = gdf_out.geometry.iloc[0]
    assert geom.has_z

    coords = list(geom.coords)
    assert len(coords) == 4
    assert [coord[2] for coord in coords] == pytest.approx([1.5, 1.5, 2.5, 2.5])
    assert gdf_out["z"].iloc[0] == pytest.approx(2.0)


def test_create_z_linestrings_from_bfe_fallback_for_missing_vertices():
    gdf_lines = gpd.GeoDataFrame(
        {"name": ["fw"]},
        geometry=[LineString([(0.0, 0.0), (250.0, 0.0)])],
        crs="EPSG:3857",
    )
    gdf_bfe = gpd.GeoDataFrame(
        {"bfe": [1.0]},
        geometry=[Polygon([(-10, -10), (120, -10), (120, 10), (-10, 10)])],
        crs="EPSG:3857",
    )

    gdf_out = create_z_linestrings_from_bfe(
        gdf_lines=gdf_lines,
        gdf_bfe=gdf_bfe,
        bfe_field_name="bfe",
        interval_m=100.0,
        elevation_offset=0.5,
    )

    geom = gdf_out.geometry.iloc[0]
    z_values = [coord[2] for coord in geom.coords]

    assert z_values == pytest.approx([1.5, 1.5, 0.5, 0.5])
    assert np.isfinite(gdf_out["z"].iloc[0])


def test_create_z_linestrings_from_bfe_raises_for_invalid_interval():
    gdf_lines = gpd.GeoDataFrame(
        {"name": ["fw"]},
        geometry=[LineString([(0.0, 0.0), (10.0, 0.0)])],
        crs="EPSG:3857",
    )
    gdf_bfe = gpd.GeoDataFrame(
        {"bfe": [1.0]},
        geometry=[Polygon([(0, -1), (20, -1), (20, 1), (0, 1)])],
        crs="EPSG:3857",
    )

    with pytest.raises(ValueError, match="interval_m"):
        create_z_linestrings_from_bfe(
            gdf_lines=gdf_lines,
            gdf_bfe=gdf_bfe,
            bfe_field_name="bfe",
            interval_m=0.0,
        )
