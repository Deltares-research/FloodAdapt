import pytest

from flood_adapt.objects import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    MeasureType,
    Pump,
    SelectionType,
)
from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import GeoDataFrameContainer


@pytest.fixture
def test_pump(gdf_container_polyline: GeoDataFrameContainer) -> Pump:
    return Pump(
        name="test_pump",
        description="test_pump",
        type=MeasureType.pump,
        discharge=us.UnitfulDischarge(value=100, units=us.UnitTypesDischarge.cfs),
        selection_type=SelectionType.polygon,
        gdf=gdf_container_polyline,
    )


@pytest.fixture
def test_elevate(gdf_container_polygon: GeoDataFrameContainer) -> Elevate:
    return Elevate(
        name="test_elevate",
        description="test_elevate",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        selection_type=SelectionType.polygon,
        property_type="RES",
        gdf=gdf_container_polygon,
    )


@pytest.fixture()
def test_elevate_aggr() -> Elevate:
    return Elevate(
        name="test_elevate_aggr",
        description="elevate_aggr_area",
        type=MeasureType.elevate_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name3",
        elevation=us.UnitfulLengthRefValue(
            value=2.0, units=us.UnitTypesLength.feet, type=us.VerticalReference.floodmap
        ),
        property_type="RES",
    )


@pytest.fixture
def test_buyout(gdf_container_polygon: GeoDataFrameContainer) -> Buyout:
    return Buyout(
        name="test_buyout",
        description="test_buyout",
        type=MeasureType.buyout_properties,
        selection_type=SelectionType.polygon,
        property_type="RES",
        gdf=gdf_container_polygon,
    )


@pytest.fixture()
def test_floodproof_aggr() -> FloodProof:
    return FloodProof(
        name="floodproof",
        type=MeasureType.floodproof_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name3",
        property_type="RES",
        elevation=us.UnitfulLengthRefValue(
            value=3.0, units=us.UnitTypesLength.feet, type=us.VerticalReference.floodmap
        ),
    )


@pytest.fixture
def test_floodproof(gdf_container_polygon: GeoDataFrameContainer) -> FloodProof:
    return FloodProof(
        name="test_floodproof",
        description="test_floodproof",
        type=MeasureType.floodproof_properties,
        selection_type=SelectionType.polygon,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        property_type="RES",
        gdf=gdf_container_polygon,
    )


@pytest.fixture
def test_green_infra(
    gdf_container_polygon: GeoDataFrameContainer,
) -> GreenInfrastructure:
    return GreenInfrastructure(
        name="test_green_infra",
        description="test_green_infra",
        type=MeasureType.greening,
        volume=us.UnitfulVolume(value=100, units=us.UnitTypesVolume.cf),
        height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.feet),
        selection_type=SelectionType.polygon,
        gdf=gdf_container_polygon,
        percent_area=10,
    )


@pytest.fixture
def test_floodwall(gdf_container_polyline: GeoDataFrameContainer) -> FloodWall:
    return FloodWall(
        name="test_seawall",
        description="seawall",
        type=MeasureType.floodwall,
        selection_type=SelectionType.polygon,
        elevation=us.UnitfulLength(value=12, units=us.UnitTypesLength.feet),
        gdf=gdf_container_polyline,
    )
