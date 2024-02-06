import pytest

from flood_adapt.object_model.interface.measures import (
    GreenInfrastructureModel,
    HazardMeasureModel,
    HazardType,
    MeasureModel,
    SelectionType,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulVolume,
    UnitTypesLength,
    UnitTypesVolume,
)


class TestMeasureModel:
    def test_measure_model_correct_input(self):
        # Arrange
        measure = MeasureModel(
            name="test_measure",
            description="test description",
            type=HazardType.floodwall,
        )

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == "test description"
        assert measure.type == "floodwall"

    def test_measure_model_no_description(self):
        # Arrange
        measure = MeasureModel(name="test_measure", type=HazardType.floodwall)

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == ""
        assert measure.type == "floodwall"

    def test_measure_model_no_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            MeasureModel(type=HazardType.floodwall)

        # Assert
        assert "validation error for MeasureModel\nname\n  field required" in str(
            excinfo.value
        )

    def test_measure_model_invalid_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            MeasureModel(name="", type=HazardType.floodwall)

        # Assert
        assert "Name cannot be empty" in str(excinfo.value)

    def test_measure_model_invalid_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            MeasureModel(
                name="test_measure", description="test description", type="invalid_type"
            )

        # Assert
        assert "MeasureModel\ntype\n  value is not a valid enumeration member" in str(
            excinfo.value
        )


class TestHazardMeasureModel:
    def test_hazard_measure_model_correct_input(self):
        # Arrange
        hazard_measure = HazardMeasureModel(
            name="test_hazard_measure",
            description="test description",
            type=HazardType.floodwall,
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
            type=HazardType.floodwall,
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
                type=HazardType.floodwall,
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
        assert (
            "HazardMeasureModel\ntype\n  value is not a valid enumeration member"
            in str(excinfo.value)
        )

    def test_hazard_measure_model_invalid_selection_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            HazardMeasureModel(
                name="test_hazard_measure",
                description="test description",
                type=HazardType.floodwall,
                polygon_file="test_polygon_file",
                selection_type="invalid_selection_type",
            )

        # Assert
        assert (
            "HazardMeasureModel\nselection_type\n  value is not a valid enumeration member"
            in str(excinfo.value)
        )


class TestGreenInfrastructureModel:
    def test_green_infrastructure_model_correct_aggregation_area_greening_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructureModel(
            name="test_green_infrastructure",
            description="test description",
            type=HazardType.greening,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.aggregation_area,
            aggregation_area_name="test_aggregation_area_name",
            aggregation_area_type="test_aggregation_area_type",
            volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
            height=UnitfulLength(value=1, units=UnitTypesLength.meters),
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
        assert green_infrastructure.volume == UnitfulVolume(
            value=1, units=UnitTypesVolume.m3
        )
        assert green_infrastructure.height == UnitfulLength(
            value=1, units=UnitTypesLength.meters
        )
        assert green_infrastructure.percent_area == 100.0

    def test_green_infrastructure_model_correct_total_storage_polygon_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructureModel(
            name="test_green_infrastructure",
            description="test description",
            type=HazardType.total_storage,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polygon,
            volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
        )  # No height or percent_area needed for total storage

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "total_storage"
        assert green_infrastructure.polygon_file == "test_polygon_file"
        assert green_infrastructure.selection_type == "polygon"
        assert green_infrastructure.volume == UnitfulVolume(
            value=1, units=UnitTypesVolume.m3
        )

    def test_green_infrastructure_model_correct_water_square_polygon_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructureModel(
            name="test_green_infrastructure",
            description="test description",
            type=HazardType.water_square,
            polygon_file="test_polygon_file",
            selection_type=SelectionType.polygon,
            volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
            height=UnitfulLength(value=1, units=UnitTypesLength.meters),
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
                type=HazardType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_type="test_aggregation_area_type",
                volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                height=UnitfulLength(value=1, units=UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert (
            "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set."
            in str(excinfo.value)
        )

    def test_green_infrastructure_model_no_aggregation_area_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructureModel(
                name="test_green_infrastructure",
                description="test description",
                type=HazardType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                height=UnitfulLength(value=1, units=UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert (
            "If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set."
            in str(excinfo.value)
        )

    def test_green_infrastructure_model_other_measure_type(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructureModel(
                name="test_green_infrastructure",
                description="test description",
                type=HazardType.floodwall,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                aggregation_area_type="test_aggregation_area_type",
                volume=UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                height=UnitfulLength(value=1, units=UnitTypesLength.meters),
                percent_area=100.0,
            )

        # Assert
        assert "GreenInfrastructureModel\ntype\n  Type must be one of " in str(
            excinfo.value
        )

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message",
        [
            (
                None,
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                100.0,
                "volume\n  none is not an allowed value",
            ),
            (
                UnitfulVolume(value=0, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                100.0,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=-1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                100.0,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                None,
                100.0,
                "Height must be a UnitfulLength",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=0, units=UnitTypesLength.meters),
                100.0,
                "Height cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=-1, units=UnitTypesLength.meters),
                100.0,
                "Height cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                None,
                "Percent area must be a float",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                -1,
                "Percent area must be between 0 and 100",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                101,
                "Percent area must be between 0 and 100",
            ),
        ],
        ids=[
            "volume_none",
            "volume_zero",
            "volume_negative",
            "height_none",
            "height_zero",
            "height_negative",
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
                type=HazardType.greening,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.aggregation_area,
                aggregation_area_name="test_aggregation_area_name",
                aggregation_area_type="test_aggregation_area_type",
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert error_message in str(excinfo.value)

    @pytest.mark.parametrize(
        "volume, height, percent_area, error_message",
        [
            (
                None,
                None,
                None,
                "volume\n  none is not an allowed value",
            ),
            (
                UnitfulVolume(value=0, units=UnitTypesVolume.m3),
                None,
                None,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=-1, units=UnitTypesVolume.m3),
                None,
                None,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                None,
                "Height cannot be set for total storage type measures",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                None,
                100,
                "Percent area cannot be set for total storage or water square type measures",
            ),
        ],
        ids=[
            "volume_none",
            "volume_zero",
            "volume_negative",
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
                type=HazardType.total_storage,
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
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                None,
                "volume\n  none is not an allowed value",
            ),
            (
                UnitfulVolume(value=0, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                None,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=-1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                None,
                "Volume cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                None,
                None,
                "Height must be a UnitfulLength",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=0, units=UnitTypesLength.meters),
                None,
                "Height cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=-1, units=UnitTypesLength.meters),
                None,
                "Height cannot be zero or negative",
            ),
            (
                UnitfulVolume(value=1, units=UnitTypesVolume.m3),
                UnitfulLength(value=1, units=UnitTypesLength.meters),
                100,
                "Percent area cannot be set for total storage or water square type measures",
            ),
        ],
        ids=[
            "volume_none",
            "volume_zero",
            "volume_negative",
            "height_none",
            "height_zero",
            "height_negative",
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
                type=HazardType.water_square,
                polygon_file="test_polygon_file",
                selection_type=SelectionType.polygon,
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert error_message in str(excinfo.value)
