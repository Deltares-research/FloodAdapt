from pathlib import Path

import geopandas as gpd
import pytest

from flood_adapt.objects.data_container import (
    CycloneTrackContainer,
    GeoDataFrameContainer,
    TropicalCyclone,
)

# -------------------------- #
# GeoDataFrames
# -------------------------- #


@pytest.fixture
def gdf_single_line(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "pump.geojson").to_crs(epsg=4326)


@pytest.fixture
def gdf_polygon(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polygon.geojson").to_crs(epsg=4326)


@pytest.fixture
def gdf_polyline(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "polyline.geojson").to_crs(epsg=4326)


@pytest.fixture
def gdf_new_areas(test_data_dir: Path) -> gpd.GeoDataFrame:
    return gpd.read_file(test_data_dir / "new_areas.geojson").to_crs(epsg=4326)


# -------------------------- #
# GeoDataFrameContainers
# -------------------------- #


@pytest.fixture
def gdf_container_single_line(
    gdf_single_line: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="single_line")
    container.set_data(gdf_single_line)
    return container


@pytest.fixture
def gdf_container_polygon(
    gdf_polygon: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="polygon")
    container.set_data(gdf_polygon)
    return container


@pytest.fixture
def gdf_container_polyline(
    gdf_polyline: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="polyline")
    container.set_data(gdf_polyline)
    return container


@pytest.fixture
def gdf_container_new_areas(
    gdf_new_areas: gpd.GeoDataFrame,
) -> GeoDataFrameContainer:
    container = GeoDataFrameContainer(name="new_areas")
    container.set_data(gdf_new_areas)
    return container


@pytest.fixture
def tropical_cyclone(cyc_file: Path) -> TropicalCyclone:
    tc = TropicalCyclone()
    tc.read_track(cyc_file, fmt="ddb_cyc")
    tc.include_rainfall = False
    return tc


@pytest.fixture
def cyclone_track_container(
    tropical_cyclone: TropicalCyclone,
) -> CycloneTrackContainer:
    container = CycloneTrackContainer(name="IAN")
    container.set_data(tropical_cyclone)
    return container
