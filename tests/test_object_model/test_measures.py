from pathlib import Path

import geopandas as gpd
import object_model.io.unitfulvalue as uv
import pytest
import tomli
from object_model.direct_impact.measure.buyout import Buyout
from object_model.direct_impact.measure.elevate import Elevate
from object_model.direct_impact.measure.floodproof import FloodProof
from object_model.hazard.measure.floodwall import FloodWall
from object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from object_model.hazard.measure.pump import Pump
from object_model.interface.measures import (
    BuyoutModel,
    ElevateModel,
    FloodProofModel,
    GreenInfrastructureModel,
    HazardType,
    ImpactType,
    PumpModel,
    SelectionType,
)


@pytest.fixture
def test_floodwall(test_data_dir):
    floodwall_model = {
        "name": "test_seawall",
        "description": "seawall",
        "type": HazardType.floodwall,
        "selection_type": SelectionType.polygon,
        "elevation": uv.UnitfulLength(value=12, units=uv.UnitTypesLength.feet),
        "polygon_file": str(test_data_dir / "polyline.geojson"),
    }
    return FloodWall(floodwall_model)


def test_floodwall_read(test_floodwall):
    assert isinstance(test_floodwall.attrs.name, str)
    assert isinstance(test_floodwall.attrs.description, str)
    assert isinstance(test_floodwall.attrs.type, HazardType)
    assert isinstance(test_floodwall.attrs.elevation, uv.UnitfulLength)

    assert test_floodwall.attrs.name == "test_seawall"
    assert test_floodwall.attrs.description == "seawall"
    assert test_floodwall.attrs.type == "floodwall"
    assert test_floodwall.attrs.elevation.value == 12
    assert test_floodwall.attrs.elevation.units == uv.UnitTypesLength.feet


def test_elevate_aggr_area_read(test_db):
    test_toml = (
        test_db.input_path
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.attrs.name, str)
    assert isinstance(elevate.attrs.description, str)
    assert isinstance(elevate.attrs.type, ImpactType)
    assert isinstance(elevate.attrs.elevation, uv.UnitfulLengthRefValue)
    assert isinstance(elevate.attrs.selection_type, SelectionType)
    assert isinstance(elevate.attrs.aggregation_area_name, str)

    assert elevate.attrs.name == "raise_property_aggregation_area"
    assert elevate.attrs.description == "raise_property_aggregation_area"
    assert elevate.attrs.type == "elevate_properties"
    assert elevate.attrs.elevation.value == 1
    assert elevate.attrs.elevation.units == uv.UnitTypesLength.feet
    assert elevate.attrs.elevation.type == "floodmap"
    assert elevate.attrs.selection_type == "aggregation_area"
    assert elevate.attrs.aggregation_area_type == "aggr_lvl_2"
    assert elevate.attrs.aggregation_area_name == "name5"


def test_elevate_aggr_area_read_fail(test_db):
    # TODO validators do not work?
    test_dict = {
        "name": "test1",
        "description": "test1",
        "type": "elevate_properties",
        "elevation": {"value": 1, "units": uv.UnitTypesLength.feet, "type": "floodmap"},
        "selection_type": "aggregation_area",
        # "aggregation_area_name": "test_area",
        "property_type": "RES",
    }

    Elevate.load_dict(test_dict)


def test_elevate_aggr_area_save(test_db):
    test_toml = (
        test_db.input_path
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area.toml"
    )

    test_toml_new = (
        test_db.input_path
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area_new.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    elevate.save(test_toml_new)

    with open(test_toml, mode="rb") as fp:
        test_toml_dict = tomli.load(fp)
    with open(test_toml_new, mode="rb") as fp:
        test_toml_dict_new = tomli.load(fp)

    assert test_toml_dict == test_toml_dict_new
    test_toml_new.unlink()


def test_elevate_polygon_read(test_db):
    test_toml = (
        test_db.input_path
        / "measures"
        / "raise_property_polygon"
        / "raise_property_polygon.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.attrs.name, str)
    assert isinstance(elevate.attrs.description, str)
    assert isinstance(elevate.attrs.type, ImpactType)
    assert isinstance(elevate.attrs.elevation, uv.UnitfulLengthRefValue)
    assert isinstance(elevate.attrs.selection_type, SelectionType)
    assert isinstance(elevate.attrs.polygon_file, str)

    assert elevate.attrs.name == "raise_property_polygon"
    assert elevate.attrs.description == "raise_property_polygon"
    assert elevate.attrs.type == "elevate_properties"
    assert elevate.attrs.elevation.value == 1
    assert elevate.attrs.elevation.units == uv.UnitTypesLength.feet
    assert elevate.attrs.elevation.type == "floodmap"
    assert elevate.attrs.selection_type == "polygon"
    assert elevate.attrs.polygon_file == "raise_property_polygon.geojson"

    polygon = gpd.read_file(Path(test_toml).parent / elevate.attrs.polygon_file)
    assert isinstance(polygon, gpd.GeoDataFrame)


def test_buyout_read(test_db):
    test_toml = test_db.input_path / "measures" / "buyout" / "buyout.toml"
    assert test_toml.is_file()

    buyout = Buyout.load_file(test_toml)

    assert isinstance(buyout.attrs.name, str)
    assert isinstance(buyout.attrs.description, str)
    assert isinstance(buyout.attrs.type, ImpactType)
    assert isinstance(buyout.attrs.selection_type, SelectionType)
    assert isinstance(buyout.attrs.aggregation_area_name, str)


def test_floodproof_read(test_db):
    test_toml = test_db.input_path / "measures" / "floodproof" / "floodproof.toml"
    assert test_toml.is_file()

    floodproof = FloodProof.load_file(test_toml)

    assert isinstance(floodproof.attrs.name, str)
    assert isinstance(floodproof.attrs.description, str)
    assert isinstance(floodproof.attrs.type, ImpactType)
    assert isinstance(floodproof.attrs.selection_type, SelectionType)
    assert isinstance(floodproof.attrs.aggregation_area_name, str)


def test_pump_read(test_db):
    test_toml = test_db.input_path / "measures" / "pump" / "pump.toml"

    assert test_toml.is_file()

    pump = Pump.load_file(test_toml)

    assert isinstance(pump.attrs.name, str)
    assert isinstance(pump.attrs.type, HazardType)
    assert isinstance(pump.attrs.discharge, uv.UnitfulDischarge)

    test_geojson = test_db.input_path / "measures" / "pump" / pump.attrs.polygon_file

    assert test_geojson.is_file()


def test_green_infra_read(test_db):
    test_toml = test_db.input_path / "measures" / "green_infra" / "green_infra.toml"

    assert test_toml.is_file()

    green_infra = GreenInfrastructure.load_file(test_toml)

    assert isinstance(green_infra.attrs.name, str)
    assert isinstance(green_infra.attrs.description, str)
    assert isinstance(green_infra.attrs.type, HazardType)
    assert isinstance(green_infra.attrs.volume, uv.UnitfulVolume)
    assert isinstance(green_infra.attrs.height, uv.UnitfulLength)

    test_geojson = (
        test_db.input_path / "measures" / "green_infra" / green_infra.attrs.polygon_file
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
    data = PumpModel(
        name="test_pump",
        description="test_pump",
        type=HazardType.pump,
        discharge=uv.UnitfulDischarge(value=100, units="cfs"),
        selection_type=SelectionType.polygon,
        polygon_file=str(test_data_dir / "polyline.geojson"),
    )
    return Pump.load_dict(
        data=data,
    )


@pytest.fixture
def test_elevate(test_db, test_data_dir):
    data = ElevateModel(
        name="test_elevate",
        description="test_elevate",
        type=ImpactType.elevate_properties,
        elevation=uv.UnitfulLengthRefValue(
            value=1, units=uv.UnitTypesLength.feet, type="floodmap"
        ),
        selection_type=SelectionType.polygon,
        property_type="RES",
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )
    return Elevate.load_dict(
        data=data,
    )


@pytest.fixture
def test_buyout(test_db, test_data_dir):
    data = BuyoutModel(
        name="test_buyout",
        description="test_buyout",
        type=ImpactType.buyout_properties,
        selection_type=SelectionType.polygon,
        property_type="RES",
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )

    return Buyout.load_dict(
        data=data,
    )


@pytest.fixture
def test_floodproof(test_db, test_data_dir):
    data = FloodProofModel(
        name="test_floodproof",
        description="test_floodproof",
        type=ImpactType.floodproof_properties,
        selection_type=SelectionType.polygon,
        elevation=uv.UnitfulLengthRefValue(
            value=1, units=uv.UnitTypesLength.feet, type=uv.VerticalReference.floodmap
        ),
        property_type="RES",
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )

    return FloodProof.load_dict(
        data=data,
    )


@pytest.fixture
def test_green_infra(test_db, test_data_dir):
    data = GreenInfrastructureModel(
        name="test_green_infra",
        description="test_green_infra",
        type=HazardType.greening,
        volume=uv.UnitfulVolume(value=100, units=uv.UnitTypesVolume.cf),
        height=uv.UnitfulHeight(value=1, units=uv.UnitTypesLength.feet),
        selection_type=SelectionType.polygon,
        polygon_file=str(test_data_dir / "polygon.geojson"),
        percent_area=10,
    )

    return GreenInfrastructure.load_dict(
        data=data,
    )


def test_pump_save_saves_geojson(test_pump, tmp_path):
    # Arrange
    output_path = tmp_path / "test_pump.toml"
    expected_geojson = output_path.parent / Path(test_pump.attrs.polygon_file).name

    # Act
    test_pump.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_pump.attrs.polygon_file == expected_geojson.name


def test_elevate_save_saves_geojson(test_elevate, tmp_path):
    # Arrange
    output_path = tmp_path / "test_elevate.toml"
    expected_geojson = output_path.parent / Path(test_elevate.attrs.polygon_file).name

    # Act
    test_elevate.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_elevate.attrs.polygon_file == expected_geojson.name


def test_buyout_save_saves_geojson(test_buyout, tmp_path):
    # Arrange
    output_path = tmp_path / "test_buyout.toml"
    expected_geojson = output_path.parent / Path(test_buyout.attrs.polygon_file).name

    # Act
    test_buyout.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_buyout.attrs.polygon_file == expected_geojson.name


def test_floodproof_save_saves_geojson(test_floodproof, tmp_path):
    # Arrange
    output_path = tmp_path / "test_floodproof.toml"
    expected_geojson = (
        output_path.parent / Path(test_floodproof.attrs.polygon_file).name
    )

    # Act
    test_floodproof.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_floodproof.attrs.polygon_file == expected_geojson.name


def test_green_infra_save_saves_geojson(test_green_infra, tmp_path):
    # Arrange
    output_path = tmp_path / "test_greeninfra.toml"
    expected_geojson = (
        output_path.parent / Path(test_green_infra.attrs.polygon_file).name
    )

    # Act
    test_green_infra.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    assert test_green_infra.attrs.polygon_file == expected_geojson.name
