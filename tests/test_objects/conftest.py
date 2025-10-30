import geopandas as gpd
import pytest


@pytest.fixture()
def gdf_single_line(test_data_dir) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "pump.geojson").to_crs(epsg=4326)


@pytest.fixture()
def gdf_polygon(test_data_dir) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polygon.geojson").to_crs(epsg=4326)


@pytest.fixture()
def gdf_polyline(test_data_dir) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polyline.geojson").to_crs(epsg=4326)
