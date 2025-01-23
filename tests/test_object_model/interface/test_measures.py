from typing import Type

import pytest
from pydantic import ValidationError

from flood_adapt.object_model.interface.measures import (
    GreenInfrastructureModel,
    HazardMeasureModel,
    MeasureModel,
    MeasureType,
    SelectionType,
)
from flood_adapt.object_model.io import unit_system as us


def assert_validation_error(
    excinfo: pytest.ExceptionInfo,
    class_name: str,
    expected_message: str,
    expected_type: Type[Exception] = ValidationError,
):
    assert (
        excinfo.value.error_count() == 1
    ), f"Expected 1 error but got {excinfo.value.error_count()}"
    assert (
        excinfo.type == expected_type
    ), f"Expected exception of type '{expected_type}' but got '{excinfo.type}'"
    assert class_name in str(
        excinfo.value
    ), f"Expected '{class_name}' in '{str(excinfo.value)}'"
    assert expected_message in str(
        excinfo.value
    ), f"Expected '{expected_message}' in '{str(excinfo.value)}'"


class TestMeasureModel:
    def test_measure_model_correct_input(self):
        # Arrange
        measure = MeasureModel(
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
        measure = MeasureModel(name="test_measure", type=MeasureType.floodwall)

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == ""
        assert measure.type == "floodwall"

    def test_measure_model_no_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            MeasureModel(type=MeasureType.floodwall)

        # Assert
        assert "validation error for MeasureModel\nname\n  Field required" in str(
            excinfo.value
        )

    def test_measure_model_invalid_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            MeasureModel(name="", type=MeasureType.floodwall)

        # Assert
        assert (
            "validation error for MeasureModel\nname\n  String should have at least 1 character "
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
            MeasureModel.model_validate(data)

        # Assert
        assert len(excinfo.value.errors()) == 1

        error = excinfo.value.errors()[0]
        assert error["type"] == "enum", error["type"]


class TestHazardMeasureModel:
    def test_hazard_measure_model_correct_input(self):
        # Arrange
        hazard_measure = HazardMeasureModel(
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
        hazard_measure = HazardMeasureModel(
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
            HazardMeasureModel(
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
            HazardMeasureModel(
                name="test_hazard_measure",
                description="test description",
                type="invalid_type",
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
            )

        # Assert
        assert "HazardMeasureModel\ntype\n  Input should be " in str(excinfo.value)

    def test_hazard_measure_model_invalid_selection_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            HazardMeasureModel(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                polygon_file="test_polygon_file",
                selection_type="invalid_selection_type",
            )

        # Assert
        assert "HazardMeasureModel\nselection_type\n  Input should be " in str(
            excinfo.value
        )


class TestGreenInfrastructureModel:
    def test_green_infrastructure_model_correct_aggregation_area_greening_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructureModel(
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
        green_infrastructure = GreenInfrastructureModel(
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
        green_infrastructure = GreenInfrastructureModel(
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
            GreenInfrastructureModel(
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
            excinfo,
            "GreenInfrastructureModel",
            "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set.",
        )

    def test_green_infrastructure_model_no_aggregation_area_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructureModel(
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
            excinfo,
            "GreenInfrastructureModel",
            "If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set.",
        )

    def test_green_infrastructure_model_other_measure_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructureModel(
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
            excinfo,
            "GreenInfrastructureModel",
            "Type must be one of 'water_square', 'greening', or 'total_storage'",
        )

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message",
        [
            (
                None,
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                100.0,
                "volume\n  Input should be a valid dictionary or instance of UnitfulVolume",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                None,
                100.0,
                "Height and percent_area needs to be set for greening type measures",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulLength(value=0, units=us.UnitTypesLength.meters),
                None,
                "height.value\n  Input should be greater than 0",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulLength(value=-1, units=us.UnitTypesLength.meters),
                None,
                "height.value\n  Input should be greater than 0",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                None,
                "Height and percent_area needs to be set for greening type measures",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                -1,
                "percent_area\n  Input should be greater than or equal to 0",
            ),
            (
                us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
                us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
                101,
                "percent_area\n  Input should be less than or equal to 100",
            ),
        ],
        ids=[
            "volume_none",
            "height_none",
            "unitfulLength_zero",  # You should still be able to set as a us.Unitfull length. However, during the conversion to height, it should trigger the height validator
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
    ):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructureModel(
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
            excinfo,
            "GreenInfrastructureModel",
            error_message,
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
            GreenInfrastructureModel(
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
        assert "1 validation error for GreenInfrastructureModel" in str(excinfo.value)
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
            GreenInfrastructureModel(
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
