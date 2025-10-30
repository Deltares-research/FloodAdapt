from pathlib import Path
from typing import Optional

import geopandas as gpd
import pytest
import tomli
from pydantic import ValidationError

from flood_adapt.objects import (
    Elevate,
    GreenInfrastructure,
    Measure,
    MeasureType,
    SelectionType,
)
from flood_adapt.objects.forcing import unit_system as us


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
            gdf="test_polygon.geojson",
        )

        # Assert
        assert measure.name == "test_measure"
        assert measure.description == "test description"
        assert measure.type == "floodwall"
        assert measure.selection_type == "polyline"
        assert measure.gdf == "test_polygon.geojson"

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
                gdf="test_polygon.geojson",
            )

        # Assert
        assert len(excinfo.value.errors()) == 1

        error = excinfo.value.errors()[0]
        assert error["type"] == "enum", error["type"]

    def test_measure_polygon_correct_input(self, gdf_polygon: gpd.GeoDataFrame):
        # Arrange
        hazard_measure = Measure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            gdf=gdf_polygon,
            selection_type=SelectionType.polygon,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert isinstance(hazard_measure.gdf, gpd.GeoDataFrame)
        assert hazard_measure.selection_type == "polygon"

    def test_measure_polyline_correct_input(self, gdf_polygon):
        # Arrange
        hazard_measure = Measure(
            name="test_hazard_measure",
            description="test description",
            type=MeasureType.floodwall,
            gdf=gdf_polygon,
            selection_type=SelectionType.polyline,
        )

        # Assert
        assert hazard_measure.name == "test_hazard_measure"
        assert hazard_measure.description == "test description"
        assert hazard_measure.type == "floodwall"
        assert isinstance(hazard_measure.gdf, gpd.GeoDataFrame)
        assert hazard_measure.selection_type == "polyline"

    @pytest.mark.parametrize(
        "selection_type",
        [
            SelectionType.polygon,
            SelectionType.polyline,
        ],
    )
    def test_measure_gdf_incorrect_input(self, selection_type):
        # Arrange
        with pytest.raises(ValidationError) as excinfo:
            Measure(
                name="test_hazard_measure",
                description="test description",
                type=MeasureType.floodwall,
                gdf=None,
                selection_type=selection_type,
            )

        # Assert
        assert_validation_error(
            excinfo=excinfo,
            class_name="Measure",
            expected_msg="If `selection_type` is 'polygon' or 'polyline', then `gdf` needs to be set.",
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
                gdf="test_polygon",
                selection_type="invalid_selection_type",
            )

        # Assert
        assert "Measure\nselection_type\n  Input should be " in str(excinfo.value)

    def test_save_and_load_with_gdf(
        self, gdf_polygon: gpd.GeoDataFrame, tmp_path: Path
    ):
        dst_toml = tmp_path / "test_measure_with_gdf.toml"
        saved = Measure(
            name="test_measure_with_gdf",
            type=MeasureType.floodwall,
            selection_type=SelectionType.polygon,
            gdf=gdf_polygon,
        )

        saved.save(dst_toml)
        assert dst_toml.is_file()
        assert (dst_toml.parent / f"{saved.name}.geojson").is_file()

        loaded = Measure.load_file(dst_toml)
        assert isinstance(loaded.gdf, gpd.GeoDataFrame)
        assert saved == loaded

    def test_save_additional_with_path(
        self, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
    ):
        path = tmp_path / "measure.geojson"
        gdf_polygon.to_file(path)
        measure = Measure(
            name="test_measure",
            description="test desc",
            type=MeasureType.floodwall,
            selection_type=SelectionType.polygon,
            gdf=path,
        )
        output_dir = tmp_path / "output"
        measure.save_additional(output_dir)

        expected_path = output_dir / path.name
        assert expected_path.exists()

    def test_save_additional_with_gdf(
        self, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
    ):
        measure = Measure(
            name="test_measure",
            description="test desc",
            type=MeasureType.floodwall,
            selection_type=SelectionType.polygon,
            gdf=gdf_polygon,
        )
        output_dir = tmp_path / "output"
        measure.save_additional(output_dir)

        expected_path = output_dir / f"{measure.name}.geojson"
        assert expected_path.exists()

    def test_save_additional_with_str(
        self, tmp_path: Path, gdf_polygon: gpd.GeoDataFrame
    ):
        path = tmp_path / "measure.geojson"
        gdf_polygon.to_file(path)
        measure = Measure(
            name="test_measure",
            description="test desc",
            type=MeasureType.floodwall,
            selection_type=SelectionType.polygon,
            gdf=path.as_posix(),
        )
        output_dir = tmp_path / "output"
        measure.save_additional(output_dir)

        expected_path = output_dir / path.name
        assert expected_path.exists()


class TestGreenInfrastructure:
    def test_green_infrastructure_model_correct_aggregation_area_greening_input(self):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.greening,
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

    def test_green_infrastructure_model_correct_total_storage_polygon_input(
        self, gdf_polygon
    ):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.total_storage,
            gdf=gdf_polygon,
            selection_type=SelectionType.polygon,
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
        )  # No height or percent_area needed for total storage

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "total_storage"
        assert isinstance(green_infrastructure.gdf, gpd.GeoDataFrame)
        assert green_infrastructure.selection_type == "polygon"
        assert green_infrastructure.volume == us.UnitfulVolume(
            value=1, units=us.UnitTypesVolume.m3
        )

    def test_green_infrastructure_model_correct_water_square_polygon_input(
        self, gdf_polygon
    ):
        # Arrange
        green_infrastructure = GreenInfrastructure(
            name="test_green_infrastructure",
            description="test description",
            type=MeasureType.water_square,
            gdf=gdf_polygon,
            selection_type=SelectionType.polygon,
            volume=us.UnitfulVolume(value=1, units=us.UnitTypesVolume.m3),
            height=us.UnitfulHeight(value=1, units=us.UnitTypesLength.meters),
        )  # No percent_area needed for water square

        # Assert
        assert green_infrastructure.name == "test_green_infrastructure"
        assert green_infrastructure.description == "test description"
        assert green_infrastructure.type == "water_square"
        assert isinstance(green_infrastructure.gdf, gpd.GeoDataFrame)
        assert green_infrastructure.selection_type == "polygon"

    def test_green_infrastructure_model_no_aggregation_area_name(self):
        # Arrange
        with pytest.raises(ValueError) as excinfo:
            GreenInfrastructure(
                name="test_green_infrastructure",
                description="test description",
                type=MeasureType.greening,
                gdf="test_polygon.geojson",
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
                gdf="test_polygon.geojson",
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
                gdf="test_polygon.geojson",
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
                gdf="test_polygon.geojson",
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
                gdf="test_polygon.geojson",
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
                gdf="test_polygon.geojson",
                selection_type=SelectionType.polygon,
                volume=volume,
                height=height,
                percent_area=percent_area,
            )

        # Assert
        assert error_message in str(excinfo.value)


def test_floodwall_read(test_floodwall):
    assert isinstance(test_floodwall.name, str)
    assert isinstance(test_floodwall.description, str)
    assert test_floodwall.type == MeasureType.floodwall
    assert isinstance(test_floodwall.elevation, us.UnitfulLength)

    assert test_floodwall.name == "test_seawall"
    assert test_floodwall.type == "floodwall"
    assert test_floodwall.elevation.value == 12
    assert test_floodwall.elevation.units == us.UnitTypesLength.feet


def test_elevate_aggr_area_read(test_elevate_aggr):
    assert isinstance(test_elevate_aggr.name, str)
    assert isinstance(test_elevate_aggr.description, str)
    assert isinstance(test_elevate_aggr.type, MeasureType)
    assert isinstance(test_elevate_aggr.elevation, us.UnitfulLengthRefValue)
    assert isinstance(test_elevate_aggr.selection_type, SelectionType)
    assert isinstance(test_elevate_aggr.aggregation_area_name, str)

    assert test_elevate_aggr.name == "test_elevate_aggr"
    assert test_elevate_aggr.type == "elevate_properties"
    assert test_elevate_aggr.elevation.value == 2.0
    assert test_elevate_aggr.elevation.units == us.UnitTypesLength.feet
    assert test_elevate_aggr.elevation.type == "floodmap"
    assert test_elevate_aggr.selection_type == "aggregation_area"
    assert test_elevate_aggr.aggregation_area_type == "aggr_lvl_2"
    assert test_elevate_aggr.aggregation_area_name == "name3"


def test_elevate_aggr_area_read_fail():
    with pytest.raises(ValidationError) as excinfo:
        Elevate(
            name="test1",
            description="test1",
            type="elevate_properties",
            elevation=us.UnitfulLengthRefValue(
                value=1,
                units=us.UnitTypesLength.feet,
                type=us.VerticalReference.floodmap,
            ),
            selection_type="aggregation_area",
            aggregation_area_name="test_area",
            property_type="RES",
        )

    assert_validation_error(
        excinfo=excinfo,
        class_name="Elevate",
        expected_msg="If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set.",
        expected_type="value_error",
    )


def test_elevate_aggr_area_save(test_elevate, tmp_path):
    test_path = tmp_path / "to_load.toml"
    test_path.parent.mkdir(exist_ok=True)

    test_elevate.name = "new_name"
    test_elevate.save(test_path)

    loaded_elevate = Elevate.load_file(test_path)

    assert loaded_elevate == test_elevate


def test_elevate_polygon_read(test_elevate):
    assert isinstance(test_elevate.name, str)
    assert isinstance(test_elevate.description, str)
    assert isinstance(test_elevate.type, MeasureType)
    assert isinstance(test_elevate.elevation, us.UnitfulLengthRefValue)
    assert isinstance(test_elevate.selection_type, SelectionType)

    assert test_elevate.name == "test_elevate"
    assert test_elevate.type == "elevate_properties"
    assert test_elevate.elevation.value == 1
    assert test_elevate.elevation.units == us.UnitTypesLength.feet
    assert test_elevate.elevation.type == "floodmap"
    assert test_elevate.selection_type == "polygon"
    assert isinstance(test_elevate.gdf, gpd.GeoDataFrame)


def test_buyout_read(test_buyout):
    assert isinstance(test_buyout.name, str)
    assert isinstance(test_buyout.description, str)
    assert isinstance(test_buyout.type, MeasureType)
    assert isinstance(test_buyout.selection_type, SelectionType)


def test_floodproof_read(test_floodproof):
    assert isinstance(test_floodproof.name, str)
    assert isinstance(test_floodproof.description, str)
    assert isinstance(test_floodproof.type, MeasureType)
    assert isinstance(test_floodproof.selection_type, SelectionType)


def test_pump_read(test_pump):
    assert isinstance(test_pump.name, str)
    assert isinstance(test_pump.type, MeasureType)
    assert isinstance(test_pump.discharge, us.UnitfulDischarge)
    assert isinstance(test_pump.gdf, gpd.GeoDataFrame)


def test_green_infra_read(test_green_infra):
    assert isinstance(test_green_infra.name, str)
    assert isinstance(test_green_infra.description, str)
    assert isinstance(test_green_infra.type, MeasureType)
    assert isinstance(test_green_infra.volume, us.UnitfulVolume)
    assert isinstance(test_green_infra.height, us.UnitfulLength)
    assert isinstance(test_green_infra.selection_type, SelectionType)
    assert isinstance(test_green_infra.gdf, gpd.GeoDataFrame)


def test_pump_save_saves_geojson(test_pump, tmp_path):
    # Arrange
    output_path = tmp_path / "test_pump.toml"
    expected_geojson = output_path.parent / f"{test_pump.name}.geojson"

    # Act
    test_pump.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    with open(output_path, "rb") as f:
        data = tomli.load(f)
        assert data["gdf"] == expected_geojson.name


def test_elevate_save_saves_geojson(test_elevate, tmp_path):
    # Arrange
    output_path = tmp_path / "test_elevate.toml"
    expected_geojson = output_path.parent / f"{test_elevate.name}.geojson"

    # Act
    test_elevate.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    with open(output_path, "rb") as f:
        data = tomli.load(f)
        assert data["gdf"] == expected_geojson.name


def test_buyout_save_saves_geojson(test_buyout, tmp_path):
    # Arrange
    output_path = tmp_path / "test_buyout.toml"
    expected_geojson = output_path.parent / f"{test_buyout.name}.geojson"

    # Act
    test_buyout.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    with open(output_path, "rb") as f:
        data = tomli.load(f)
        assert data["gdf"] == expected_geojson.name


def test_floodproof_save_saves_geojson(test_floodproof, tmp_path):
    # Arrange
    output_path = tmp_path / "test_floodproof.toml"
    expected_geojson = output_path.parent / f"{test_floodproof.name}.geojson"

    # Act
    test_floodproof.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    with open(output_path, "rb") as f:
        data = tomli.load(f)
        assert data["gdf"] == expected_geojson.name


def test_green_infra_save_saves_geojson(test_green_infra, tmp_path):
    # Arrange
    output_path = tmp_path / "test_greeninfra.toml"
    expected_geojson = output_path.parent / f"{test_green_infra.name}.geojson"

    # Act
    test_green_infra.save(output_path)

    # Assert
    assert output_path.exists()
    assert expected_geojson.exists()
    with open(output_path, "rb") as f:
        data = tomli.load(f)
        assert data["gdf"] == expected_geojson.name
