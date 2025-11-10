from pathlib import Path

import geopandas as gpd
import pytest

from flood_adapt.objects.data_container import GeoDataFrameContainer

# -------------------------- #
# GeoDataFrames
# -------------------------- #


@pytest.fixture()
def gdf_single_line(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "pump.geojson").to_crs(epsg=4326)


@pytest.fixture()
def gdf_polygon(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polygon.geojson").to_crs(epsg=4326)


@pytest.fixture()
def gdf_polyline(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polyline.geojson").to_crs(epsg=4326)


# -------------------------- #
# GeoDataFrameContainers
# -------------------------- #


@pytest.fixture()
def gdf_container_single_line(
    gdf_single_line: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="single_line")
    container.set_data(gdf_single_line)
    return container


@pytest.fixture()
def gdf_container_polygon(
    gdf_polygon: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="polygon")
    container.set_data(gdf_polygon)
    return container


@pytest.fixture()
def gdf_container_polyline(
    gdf_polyline: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="polyline")
    container.set_data(gdf_polyline)
    return container
