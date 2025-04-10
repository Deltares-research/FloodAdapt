from pathlib import Path
from tempfile import gettempdir

import geopandas as gpd
import pytest

from flood_adapt.object_model.interface.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    MeasureType,
    Pump,
    SelectionType,
)
from flood_adapt.object_model.io import unit_system as us


@pytest.fixture
def test_floodwall(test_data_dir):
    floodwall_model = {
        "name": "test_seawall",
        "description": "seawall",
        "type": MeasureType.floodwall,
        "selection_type": SelectionType.polygon,
        "elevation": {"value": 12, "units": us.UnitTypesLength.feet.value},
        "polygon_file": str(test_data_dir / "polyline.geojson"),
    }
    return FloodWall(**floodwall_model)


def test_floodwall_read(test_floodwall):
    assert isinstance(test_floodwall.name, str)
    assert isinstance(test_floodwall.description, str)
    assert test_floodwall.type == MeasureType.floodwall
    assert isinstance(test_floodwall.elevation, us.UnitfulLength)

    assert test_floodwall.name == "test_seawall"
    assert test_floodwall.type == "floodwall"
    assert test_floodwall.elevation.value == 12
    assert test_floodwall.elevation.units == us.UnitTypesLength.feet


def test_elevate_aggr_area_read(test_db):
    test_toml = (
        test_db.input_path
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.name, str)
    assert isinstance(elevate.description, str)
    assert isinstance(elevate.type, MeasureType)
    assert isinstance(elevate.elevation, us.UnitfulLengthRefValue)
    assert isinstance(elevate.selection_type, SelectionType)
    assert isinstance(elevate.aggregation_area_name, str)

    assert elevate.name == "raise_property_aggregation_area"
    assert elevate.type == "elevate_properties"
    assert elevate.elevation.value == 1
    assert elevate.elevation.units == us.UnitTypesLength.feet
    assert elevate.elevation.type == "floodmap"
    assert elevate.selection_type == "aggregation_area"
    assert elevate.aggregation_area_type == "aggr_lvl_2"
    assert elevate.aggregation_area_name == "name5"


def test_elevate_aggr_area_read_fail(test_db):
    test_dict = {
        "name": "test1",
        "description": "test1",
        "type": "elevate_properties",
        "elevation": {
            "value": 1,
            "units": us.UnitTypesLength.feet.value,
            "type": "floodmap",
        },
        "selection_type": "aggregation_area",
        "aggregation_area_name": "test_area",
        "property_type": "RES",
    }

    Elevate(**test_dict)


def test_elevate_aggr_area_save():
    elevate = Elevate(
        name="raise_property_aggregation_area",
        description="raise_property_aggregation_area",
        type=MeasureType.elevate_properties,
        elevation=us.UnitfulLengthRefValue(
            value=1,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name5",
        property_type="RES",
    )
    test_path = Path(gettempdir()) / "to_load.toml"
    test_path.parent.mkdir(exist_ok=True)

    elevate.name = "new_name"
    elevate.save(test_path)

    loaded_elevate = Elevate.load_file(test_path)

    assert loaded_elevate == elevate


def test_elevate_polygon_read(test_db):
    test_toml = (
        test_db.input_path
        / "measures"
        / "raise_property_polygon"
        / "raise_property_polygon.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.name, str)
    assert isinstance(elevate.description, str)
    assert isinstance(elevate.type, MeasureType)
    assert isinstance(elevate.elevation, us.UnitfulLengthRefValue)
    assert isinstance(elevate.selection_type, SelectionType)
    assert isinstance(elevate.polygon_file, str)

    assert elevate.name == "raise_property_polygon"
    assert elevate.type == "elevate_properties"
    assert elevate.elevation.value == 1
    assert elevate.elevation.units == us.UnitTypesLength.feet
    assert elevate.elevation.type == "floodmap"
    assert elevate.selection_type == "polygon"
    assert elevate.polygon_file == "raise_property_polygon.geojson"

    polygon = gpd.read_file(Path(test_toml).parent / elevate.polygon_file)
    assert isinstance(polygon, gpd.GeoDataFrame)


def test_buyout_read(test_db):
    test_toml = test_db.input_path / "measures" / "buyout" / "buyout.toml"
    assert test_toml.is_file()

    buyout = Buyout.load_file(test_toml)

    assert isinstance(buyout.name, str)
    assert isinstance(buyout.description, str)
    assert isinstance(buyout.type, MeasureType)
    assert isinstance(buyout.selection_type, SelectionType)
    assert isinstance(buyout.aggregation_area_name, str)


def test_floodproof_read(test_db):
    test_toml = test_db.input_path / "measures" / "floodproof" / "floodproof.toml"
    assert test_toml.is_file()

    floodproof = FloodProof.load_file(test_toml)

    assert isinstance(floodproof.name, str)
    assert isinstance(floodproof.description, str)
    assert isinstance(floodproof.type, MeasureType)
    assert isinstance(floodproof.selection_type, SelectionType)
    assert isinstance(floodproof.aggregation_area_name, str)


def test_pump_read(test_db):
    test_toml = test_db.input_path / "measures" / "pump" / "pump.toml"

    assert test_toml.is_file()

    pump = Pump.load_file(test_toml)

    assert isinstance(pump.name, str)
    assert isinstance(pump.type, MeasureType)
    assert isinstance(pump.discharge, us.UnitfulDischarge)

    test_geojson = test_db.input_path / "measures" / "pump" / pump.polygon_file

    assert test_geojson.is_file()


def test_green_infra_read(test_db):
    test_toml = test_db.input_path / "measures" / "green_infra" / "green_infra.toml"

    assert test_toml.is_file()

    green_infra = GreenInfrastructure.load_file(test_toml)

    assert isinstance(green_infra.name, str)
    assert isinstance(green_infra.description, str)
    assert isinstance(green_infra.type, MeasureType)
    assert isinstance(green_infra.volume, us.UnitfulVolume)
    assert isinstance(green_infra.height, us.UnitfulLength)

    test_geojson = (
        test_db.input_path / "measures" / "green_infra" / green_infra.polygon_file
    )

    assert test_geojson.is_file()

    # def test_calculate_area():
    #     test_toml = (
    #         test_database
    #         / "charleston"
    #         / "input"
    #         / "measures"
    #         / "green_infra"
    #         / "green_infra.toml"
    #     )


@pytest.fixture
def test_pump(test_db, test_data_dir):
    return Pump(
        name="test_pump",
        description="test_pump",
        type=MeasureType.pump,
        discharge=us.UnitfulDischarge(value=100, units=us.UnitTypesDischarge.cfs),
        selection_type=SelectionType.polygon,
        polygon_file=str(test_data_dir / "polyline.geojson"),
    )


@pytest.fixture
def test_elevate(test_db, test_data_dir):
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
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )


@pytest.fixture
def test_buyout(test_db, test_data_dir):
    return Buyout(
        name="test_buyout",
        description="test_buyout",
        type=MeasureType.buyout_properties,
        selection_type=SelectionType.polygon,
        property_type="RES",
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )


@pytest.fixture
def test_floodproof(test_db, test_data_dir):
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
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )


@pytest.fixture
def test_green_infra(test_db, test_data_dir):
    return GreenInfrastructure(
        name="test_green_infra",
        description="test_green_infra",
        type=MeasureType.greening,
        volume=us.UnitfulVolume(value=100, units=us.UnitTypesVolume.cf),
        height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.feet),
        selection_type=SelectionType.polygon,
        polygon_file=str(test_data_dir / "polygon.geojson"),
        percent_area=10,
    )


def test_pump_save_saves_geojson(test_pump, tmp_path):
    # Arrange
    output_path = tmp_path / "test_pump.toml"
    expected_geojson = output_path.parent / Path(test_pump.polygon_file).name

    # Act
    test_pump.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_pump.polygon_file == expected_geojson.name


def test_elevate_save_saves_geojson(test_elevate, tmp_path):
    # Arrange
    output_path = tmp_path / "test_elevate.toml"
    expected_geojson = output_path.parent / Path(test_elevate.polygon_file).name

    # Act
    test_elevate.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_elevate.polygon_file == expected_geojson.name


def test_buyout_save_saves_geojson(test_buyout, tmp_path):
    # Arrange
    output_path = tmp_path / "test_buyout.toml"
    expected_geojson = output_path.parent / Path(test_buyout.polygon_file).name

    # Act
    test_buyout.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_buyout.polygon_file == expected_geojson.name


def test_floodproof_save_saves_geojson(test_floodproof, tmp_path):
    # Arrange
    output_path = tmp_path / "test_floodproof.toml"
    expected_geojson = output_path.parent / Path(test_floodproof.polygon_file).name

    # Act
    test_floodproof.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_floodproof.polygon_file == expected_geojson.name


def test_green_infra_save_saves_geojson(test_green_infra, tmp_path):
    # Arrange
    output_path = tmp_path / "test_greeninfra.toml"
    expected_geojson = output_path.parent / Path(test_green_infra.polygon_file).name

    # Act
    test_green_infra.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_green_infra.polygon_file == expected_geojson.name
