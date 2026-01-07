import geopandas as gpd
import pytest
from shapely.geometry import Point

from flood_adapt.objects.data_container import (
    GeoDataFrameContainer,
)


@pytest.fixture
def sample_geodataframe() -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )
    return gdf


def test_geodataref_read_write(tmp_path, sample_geodataframe):
    shp_path = tmp_path / "points.geojson"
    sample_geodataframe.to_file(shp_path, driver="GeoJSON")

    ref = GeoDataFrameContainer(path=shp_path)
    ref.read()
    assert isinstance(ref.data, gpd.GeoDataFrame)
    assert ref.has_data()

    # Write and re-read to confirm equality
    out_path = tmp_path / "points_copy.geojson"
    ref.path = out_path
    ref.write()
    ref2 = GeoDataFrameContainer(path=out_path)
    ref2.read()

    assert ref == ref2


def test_geodataframe_missing_crs_is_set(tmp_path, sample_geodataframe):
    gdf = sample_geodataframe.copy()
    gdf = gdf.set_crs(None, allow_override=True)

    path = tmp_path / "no_crs.geojson"
    gdf.to_file(path, driver="GeoJSON")

    ref = GeoDataFrameContainer(path=path)
    ref.read()

    assert ref.data.crs.to_epsg() == 4326


def test_geodataframe_crs_normalized(tmp_path, sample_geodataframe):
    shp_path = tmp_path / "points.geojson"
    sample_geodataframe.to_file(shp_path, driver="GeoJSON")

    ref = GeoDataFrameContainer(path=shp_path)
    ref.read()

    assert ref.data.crs.to_epsg() == 4326
