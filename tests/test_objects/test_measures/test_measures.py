from pathlib import Path
from tempfile import gettempdir
from typing import Optional

import geopandas as gpd
import pytest
from pydantic import ValidationError

from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    HazardMeasure,
    Measure,
    MeasureType,
    Pump,
    SelectionType,
)


def assert_validation_error(
    excinfo: pytest.ExceptionInfo,
    class_name: str,
    expected_loc: Optional[str] = None,
    expected_msg: Optional[str] = None,
    expected_type: Optional[str] = None,
):
    assert (
        excinfo.value.error_count() == 1
    ), f"Expected 1 error but got {excinfo.value.error_count()}"
    error = excinfo.value.errors()[0]

    assert class_name in str(
        excinfo.value
    ), f"Expected class_name: '{class_name}' in '{str(excinfo.value)}'"

    if expected_loc is not None:
        assert (
            error["loc"] == expected_loc
        ), f"Expected loc: '{expected_loc}' in '{error['loc']}'"

    if expected_type is not None:
        assert (
            error["type"] == expected_type
        ), f"Expected type: '{expected_type}' but got '{error['type']}'"

    if expected_msg is not None:
        assert (
            expected_msg in error["msg"]
        ), f"Expected msg: '{expected_msg}' but got '{error['msg']}'"


class TestMeasure:
    def test_measure_model_correct_input(self):
        # Arrange
        measure = Measure(
            name="test_measure",
            description="test description",
            type=MeasureType.floodwall,
        )

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == "test description"
        assert measure.type == "floodwall"

    def test_measure_model_no_description(self):
        # Arrange
        measure = Measure(name="test_measure", type=MeasureType.floodwall)

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == ""
        assert measure.type == "floodwall"

    def test_measure_model_no_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(type=MeasureType.floodwall)

        # Assert
        assert "validation error for Measure\nname\n  Field required" in str(
            excinfo.value
        )

    def test_measure_model_invalid_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(name="", type=MeasureType.floodwall)

        # Assert
        assert (
            "validation error for Measure\nname\n  String should have at least 1 character "
            in str(excinfo.value)
        )

    def test_measure_model_invalid_type(self):
        # Arrange
        with pytest.raises(ValidationError) as excinfo:
            data = {
                "name": "test_measure",
                "description": "test description",
                "type": "invalid_type",
            }
            Measure.model_validate(data)

        # Assert
        assert len(excinfo.value.errors()) == 1

        error = excinfo.value.errors()[0]
        assert error["type"] == "enum", error["type"]


class TestHazardMeasure:
    def test_hazard_measure_model_correct_input(self):
        # Arrange
        hazard_measure = HazardMeasure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.aggregation_area,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert hazard_measure.polygon_file == "test_polygon_file"
        assert hazard_measure.selection_type == "aggregation_area"

    def test_hazard_measure_model_no_polygon_file_aggregation_area(self):
        # Arrange
        hazard_measure = HazardMeasure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            selection_type=SelectionType.aggregation_area,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert hazard_measure.polygon_file is None
        assert hazard_measure.selection_type == "aggregation_area"

    def test_hazard_measure_model_no_polygon_file_polygon_input(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            HazardMeasure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                selection_type=SelectionType.polygon,
            )

        # Assert
        assert "`polygon_file` needs to be set" in str(excinfo.value)

    def test_hazard_measure_model_invalid_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            HazardMeasure(
                name="test_hazard_measure",
                description="test description",
                type="invalid_type",
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
            )

        # Assert
        assert "HazardMeasure\ntype\n  Input should be " in str(excinfo.value)

    def test_hazard_measure_model_invalid_selection_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            HazardMeasure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                polygon_file="test_polygon_file",
                selection_type="invalid_selection_type",
            )

        # Assert
        assert "HazardMeasure\nselection_type\n  Input should be " in str(excinfo.value)


class TestGreenInfrastructure:
    def test_green_infrastructure_model_correct_aggregation_area_greening_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.greening,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.aggregation_area,
            aggregation_area_name="test_aggregation_area_name",
            aggregation_area_type="test_aggregation_area_type",
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
            height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
            percent_area=100.0,
        )

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "greening"
        assert green_infrastructure.polygon_file == "test_polygon_file"
        assert green_infrastructure.selection_type == "aggregation_area"
        assert (
            green_infrastructure.aggregation_area_name == "test_aggregation_area_name"
        )
        assert (
            green_infrastructure.aggregation_area_type == "test_aggregation_area_type"
        )
        assert green_infrastructure.volume == us.UnitfulVolume(
            value=1, units=us.UnitTypesVolume.m3
        )
        assert green_infrastructure.height == us.UnitfulHeight(
            value=1, units=us.UnitTypesLength.meters
        )
        assert green_infrastructure.percent_area == 100.0

    def test_green_infrastructure_model_correct_total_storage_polygon_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.total_storage,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polygon,
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
        )  # No height or percent_area needed for total storage

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "total_storage"
        assert green_infrastructure.polygon_file == "test_polygon_file"
        assert green_infrastructure.selection_type == "polygon"
        assert green_infrastructure.volume == us.UnitfulVolume(
            value=1, units=us.UnitTypesVolume.m3
        )

    def test_green_infrastructure_model_correct_water_square_polygon_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.water_square,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polygon,
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
            height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
        )  # No percent_area needed for water square

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "water_square"
        assert green_infrastructure.polygon_file == "test_polygon_file"
        assert green_infrastructure.selection_type == "polygon"

    def test_green_infrastructure_model_no_aggregation_area_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_type="test_aggregation_area_type",
                volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="GreenInfrastructure",
            expected_msg="If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set.",
        )

    def test_green_infrastructure_model_no_aggregation_area_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="GreenInfrastructure",
            expected_msg="If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set.",
        )

    def test_green_infrastructure_model_other_measure_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.floodwall,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                aggregation_area_type="test_aggregation_area_type",
                volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="GreenInfrastructure",
            expected_msg="Type must be one of 'water_square', 'greening', or 'total_storage'",
        )

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message, error_loc, error_type",
        [
            (
                None,
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                100.0,
                "Input should be a valid dictionary or instance of UnitfulVolume",
                ("volume",),
                "model_type",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                None,
                100.0,
                "Height and percent_area needs to be set for greening type measures",
                (),
                "value_error",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulLength(value=-1, units=us.UnitTypesLength.meters),
                None,
                "Input should be greater than or equal to 0",
                (
                    "height",
                    "value",
                ),
                "greater_than_equal",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                None,
                "Height and percent_area needs to be set for greening type measures",
                (),
                "value_error",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                -1,
                "Input should be greater than or equal to 0",
                ("percent_area",),
                "greater_than_equal",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                101,
                "Input should be less than or equal to 100",
                ("percent_area",),
                "less_than_equal",
            ),
        ],
        ids=[
            "volume_none",
            "height_none",
            "unitfulLength_negative",  # You should still be able to set as a us.Unitfull length. However, during the conversion to height, it should trigger the height validator
            "percent_area_none",
            "percent_area_negative",
            "percent_area_above_100",
        ],
    )
    def test_green_infrastructure_model_greening_fails(
        self,
        volume,
        height,
        percent_area,
        error_message,
        error_loc,
        error_type,
    ):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                aggregation_area_type="test_aggregation_area_type",
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="GreenInfrastructure",
            expected_msg=error_message,
            expected_loc=error_loc,
            expected_type=error_type,
        )

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message",
        [
            (
                None,
                None,
                None,
                "volume\n  Input should be a valid dictionary or instance of UnitfulVolume",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                None,
                "Height and percent_area cannot be set for total storage type measures",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                None,
                100,
                "Height and percent_area cannot be set for total storage type measures",
            ),
        ],
        ids=[
            "volume_none",
            "height_set",
            "percent_area_set",
        ],
    )
    def test_green_infrastructure_model_total_storage_fails(
        self,
        volume,
        height,
        percent_area,
        error_message,
    ):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.total_storage,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.polygon,
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert "1 validation error for GreenInfrastructure" in str(excinfo.value)
        assert error_message in str(excinfo.value)

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message",
        [
            (
                None,
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                None,
                "volume\n  Input should be a valid dictionary or instance of UnitfulVolume",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                None,
                None,
                "Height needs to be set for water square type measures",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                100,
                "Percentage_area cannot be set for water square type measures",
            ),
        ],
        ids=[
            "volume_none",
            "height_none",
            "percent_area_set",
        ],
    )
    def test_green_infrastructure_model_water_square_fails(
        self,
        volume,
        height,
        percent_area,
        error_message,
    ):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.water_square,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.polygon,
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert error_message in str(excinfo.value)


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
