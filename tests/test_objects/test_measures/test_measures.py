from pathlib import Path
from typing import Optional

import pytest
from pydantic import ValidationError

from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    Measure,
    MeasureType,
    Pump,
    SelectionType,
)
from tests.test_objects import assert_object_save_load_eq


def assert_measure_save_load_eq(
    write_path: Path, obj: Measure, cls: type[Measure], load_kwargs: dict | None = None
):
    loaded = assert_object_save_load_eq(write_path, obj, cls, load_kwargs)
    if obj.polygon_file:
        assert loaded.polygon_file is not None
        assert Path(loaded.polygon_file).is_absolute()
        assert Path(loaded.polygon_file).is_file()


def assert_validation_error(
    excinfo: pytest.ExceptionInfo,
    class_name: str,
    expected_loc: Optional[tuple[str]] = None,
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
            selection_type=SelectionType.polyline,
            polygon_file="test_polygon_file.geojson",
        )

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == "test description"
        assert measure.type == "floodwall"
        assert measure.selection_type == "polyline"
        assert measure.polygon_file == "test_polygon_file.geojson"

    @pytest.mark.parametrize(
        "missing_variable",
        [
            "name",
            "type",
            "selection_type",
        ],
    )
    def test_measure_model_missing_variables(self, missing_variable):
        # Arrange
        attrs = {
            "name": "test_measure",
            "type": MeasureType.floodwall,
            "selection_type": SelectionType.all,
        }
        attrs.pop(missing_variable)

        with pytest.raises(ValueError) as excinfo:
            Measure(**attrs)

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="Measure",
            expected_loc=(missing_variable,),
            expected_type="missing",
        )

    def test_measure_model_invalid_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(name="", type=MeasureType.floodwall)

        # Assert
        assert "Name must be at least one character long" in str(excinfo.value)

    def test_measure_model_invalid_type(self):
        # Arrange
        with pytest.raises(ValidationError) as excinfo:
            Measure(
                name="test_measure",
                description="test description",
                type="invalid_type",
                selection_type=SelectionType.polyline,
                polygon_file="test_polygon_file.geojson",
            )

        # Assert
        assert len(excinfo.value.errors()) == 1

        error = excinfo.value.errors()[0]
        assert error["type"] == "enum", error["type"]

    def test_measure_polygon_correct_input(self):
        # Arrange
        hazard_measure = Measure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polygon,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert hazard_measure.polygon_file == "test_polygon_file"
        assert hazard_measure.selection_type == "polygon"

    def test_measure_polyline_correct_input(self):
        # Arrange
        hazard_measure = Measure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polyline,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert hazard_measure.polygon_file == "test_polygon_file"
        assert hazard_measure.selection_type == "polyline"

    @pytest.mark.parametrize(
        "selection_type",
        [
            SelectionType.polygon,
            SelectionType.polyline,
        ],
    )
    def test_measure_polygon_file_incorrect_input(self, selection_type):
        # Arrange
        with pytest.raises(ValidationError) as excinfo:
            Measure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                polygon_file=None,
                selection_type=selection_type,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="Measure",
            expected_msg="If `selection_type` is 'polygon' or 'polyline', then `polygon_file` needs to be set.",
            expected_type="value_error",
        )

    def test_measure_aggregation_area_correct(self):
        # Arrange
        measure = Measure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            selection_type=SelectionType.aggregation_area,
            aggregation_area_name="test_aggregation_area_name",
            aggregation_area_type="test_aggregation_area_type",
        )

        # Assert
        assert measure.name == "test_hazard_measure"
        assert measure.description == "test description"
        assert measure.type == "floodwall"
        assert measure.polygon_file is None
        assert measure.selection_type == "aggregation_area"
        assert measure.aggregation_area_name == "test_aggregation_area_name"
        assert measure.aggregation_area_type == "test_aggregation_area_type"

    def test_measure_aggregation_area_missing_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
            )
        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="Measure",
            expected_msg="If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set.",
            expected_type="value_error",
        )

    def test_measure_aggregation_area_missing_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                selection_type=SelectionType.aggregation_area,
                aggregation_area_type="test_aggregation_area_type",
            )
        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="Measure",
            expected_msg="If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set.",
            expected_type="value_error",
        )

    def test_measure_model_invalid_selection_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            Measure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                polygon_file="test_polygon_file",
                selection_type="invalid_selection_type",
            )

        # Assert
        assert "Measure\nselection_type\n  Input should be " in str(excinfo.value)


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


def test_floodwall_read(tmp_path: Path, test_floodwall):
    assert_measure_save_load_eq(tmp_path, test_floodwall, FloodWall)


def test_elevate_aggr_area_save(raise_property_aggregation_area, tmp_path):
    assert_measure_save_load_eq(tmp_path, raise_property_aggregation_area, Elevate)


def test_elevate_polygon_read(raise_property_polygon, tmp_path):
    assert_measure_save_load_eq(tmp_path, raise_property_polygon, Elevate)


def test_buyout_read(tmp_path, test_buyout):
    assert_measure_save_load_eq(tmp_path, test_buyout, Buyout)


def test_floodproof_read(tmp_path, test_floodproof):
    assert_measure_save_load_eq(tmp_path, test_floodproof, FloodProof)


def test_pump_read(tmp_path, test_pump):
    assert_measure_save_load_eq(tmp_path, test_pump, Pump)


def test_green_infra_read(tmp_path, test_green_infra):
    assert_measure_save_load_eq(tmp_path, test_green_infra, GreenInfrastructure)


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


@pytest.fixture
def raise_property_aggregation_area():
    return Elevate(
        name="raise_property_aggregation_area",
        description="",
        type=MeasureType.elevate_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name5",
        property_type="RES",
        elevation=us.UnitfulLengthRefValue(
            value=1.0,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
    )


@pytest.fixture
def raise_property_polygon(test_data_dir: Path):
    return Elevate(
        name="raise_property_polygon",
        type=MeasureType.elevate_properties,
        selection_type=SelectionType.polygon,
        polygon_file=(test_data_dir / "raise_property_polygon.geojson").as_posix(),
        property_type="RES",
        elevation=us.UnitfulLengthRefValue(
            value=1.0,
            units=us.UnitTypesLength.feet,
            type=us.VerticalReference.floodmap,
        ),
    )


@pytest.fixture
def test_pump(test_data_dir):
    return Pump(
        name="test_pump",
        description="test_pump",
        type=MeasureType.pump,
        discharge=us.UnitfulDischarge(value=100, units=us.UnitTypesDischarge.cfs),
        selection_type=SelectionType.polygon,
        polygon_file=str(test_data_dir / "polyline.geojson"),
    )


@pytest.fixture
def test_elevate(test_data_dir):
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
def test_buyout(test_data_dir):
    return Buyout(
        name="test_buyout",
        description="test_buyout",
        type=MeasureType.buyout_properties,
        selection_type=SelectionType.polygon,
        property_type="RES",
        polygon_file=str(test_data_dir / "polygon.geojson"),
    )


@pytest.fixture
def test_floodproof(test_data_dir):
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
def test_green_infra(test_data_dir):
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
