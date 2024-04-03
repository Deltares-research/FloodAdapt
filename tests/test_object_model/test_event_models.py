from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from flood_adapt.object_model.interface.events import (
    EventModel,
    HurricaneModel,
    Mode,
    OffShoreModel,
    OverlandModel,
    RainfallModel,
    RainfallSource,
    RiverDischargeModel,
    ShapeType,
    SurgeModel,
    TideModel,
    TideSource,
    TimeModel,
    TimeseriesModel,
    TranslationModel,
    WindModel,
    WindSource,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
    UnitTypesVelocity,
)
from tests.test_io.test_timeseries import TestTimeseriesModel


class TestWindModel:
    @staticmethod
    def get_test_model():
        # Arange
        _WIND_MODEL = {
            "source": WindSource.constant.value,
            "constant_speed": {"value": 10, "units": UnitTypesVelocity.mps},
            "constant_direction": {"value": 90, "units": UnitTypesDirection.degrees},
            "timeseries_file": "data.csv",
        }
        return deepcopy(_WIND_MODEL)

    @pytest.mark.skip("WindSource.map not implemented")
    def test_validate_WindModel_valid_input_WindSource_map(self):
        pass

    @pytest.mark.skip("WindSource.track not implemented")
    def test_validate_WindModel_valid_input_WindSource_track(self):
        pass

    def test_validate_WindModel_valid_input_WindSource_timeseries(self, tmp_path):
        # Arange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_test_model()
        model["timeseries_file"] = Path(temp_file)

        # Act
        wind_model = WindModel.model_validate(model)

        # Assert
        assert wind_model.source == WindSource.constant
        assert wind_model.constant_speed == UnitfulVelocity(10, UnitTypesVelocity.mps)
        assert wind_model.constant_direction == UnitfulDirection(
            90, UnitTypesDirection.degrees
        )
        assert wind_model.timeseries_file == Path(temp_file)
        assert temp_file.exists()

    def test_validate_WindModel_valid_input_WindSource_constant(self):
        # Arange
        model = self.get_test_model()
        model.pop("timeseries_file")

        # Act
        wind_model = WindModel.model_validate(model)

        # Assert
        assert wind_model.source == WindSource.constant
        assert wind_model.constant_speed == UnitfulVelocity(10, UnitTypesVelocity.mps)
        assert wind_model.constant_direction == UnitfulDirection(
            90, UnitTypesDirection.degrees
        )
        assert wind_model.timeseries_file is None

    def test_validate_windModel_timeseries_file_not_set(self):
        # Arange
        model = self.get_test_model()
        model["source"] = WindSource.timeseries.value
        model.pop("timeseries_file")

        # Act
        with pytest.raises(ValidationError) as e:
            WindModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "Timeseries file must be set when source is timeseries"
        )

    def test_validate_windModel_timeseries_file_not_csv(self):
        # Arange
        model = self.get_test_model()
        model["source"] = WindSource.timeseries.value
        model["timeseries_file"] = "data.txt"

        # Act
        with pytest.raises(ValidationError) as e:
            WindModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0] == "Timeseries file must be a .csv file"
        )

    def test_validate_windModel_timeseries_file_not_exists(self):
        # Arange
        model = self.get_test_model()
        model["source"] = WindSource.timeseries.value

        # Act
        with pytest.raises(ValidationError) as e:
            WindModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0] == "Timeseries file must be a valid file"
        )

    def test_validate_windModel_constant_speed_not_set(self):
        # Arange
        model = self.get_test_model()
        model["source"] = WindSource.constant.value
        model.pop("constant_speed")

        # Act
        with pytest.raises(ValidationError) as e:
            WindModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "Constant speed must be set when source is constant"
        )

    def test_validate_windModel_constant_direction_not_set(self):
        # Arange
        model = self.get_test_model()
        model["source"] = WindSource.constant.value
        model.pop("constant_direction")

        # Act
        with pytest.raises(ValidationError) as e:
            WindModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "Constant direction must be set when source is constant"
        )


class TestRainfallModel:
    @staticmethod
    def get_test_model():
        # Arange
        _RAINFALL_MODEL = {
            "source": RainfallSource.timeseries.value,
            "increase": 20,
            "timeseries": {
                "shape_type": ShapeType.constant,
                "start_time": {
                    "value": 0,
                    "units": UnitTypesTime.hours,
                },
                "end_time": {
                    "value": 10,
                    "units": UnitTypesTime.hours,
                },
                "peak_intensity": {
                    "value": 1,
                    "units": UnitTypesIntensity.mm_hr,
                },
            },
        }
        return deepcopy(_RAINFALL_MODEL)

    def test_validate_RainfallModel_valid_input_RainfallSource_timeseries(self):
        # Arange
        model = self.get_test_model()

        # Act
        rainfall_model = RainfallModel.model_validate(model)

        # Assert
        assert rainfall_model.source == RainfallSource.timeseries
        assert rainfall_model.increase == 20
        assert rainfall_model.timeseries.shape_type == ShapeType.constant
        assert rainfall_model.timeseries.start_time == UnitfulTime(
            0, UnitTypesTime.hours
        )
        assert rainfall_model.timeseries.end_time == UnitfulTime(
            10, UnitTypesTime.hours
        )
        assert rainfall_model.timeseries.peak_intensity == UnitfulIntensity(
            1, UnitTypesIntensity.mm_hr
        )

    @pytest.mark.skip("RainfallSource.track not implemented")
    def test_validate_RainfallModel_valid_input_RainfallSource_track(self):
        # Arange
        # Act
        # Assert
        pass

    @pytest.mark.skip("RainfallSource.map not implemented")
    def test_validate_RainfallModel_valid_input_RainfallSource_map(self):
        # Arange
        # Act
        # Assert
        pass

    def test_validate_RainfallModel_invalid_input_increase_cannot_be_negative(self):
        # Arange
        model = self.get_test_model()
        model["increase"] = -10

        # Act
        with pytest.raises(ValidationError) as e:
            RainfallModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert errors[0]["ctx"]["error"].args[0] == "Increase must be positive"

    def test_validate_RainfallModel_invalid_input_timeseriesmodel_must_be_set_when_source_is_timeseries(
        self,
    ):
        # Arange
        model = self.get_test_model()
        model.pop("timeseries")

        # Act
        with pytest.raises(ValidationError) as e:
            RainfallModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "TimeseriesModel must be set when source is timeseries"
        )


class TestRiverDischargeModel:
    @staticmethod
    def get_test_model():
        _RIVER_DISCHARGE_MODEL = {
            "base_discharge": {
                "value": 10,
                "units": UnitTypesDischarge.cms,
            },
            "timeseries": {
                "shape_type": ShapeType.constant,
                "start_time": {
                    "value": 0,
                    "units": UnitTypesTime.hours,
                },
                "end_time": {
                    "value": 10,
                    "units": UnitTypesTime.hours,
                },
                "peak_intensity": {
                    "value": 11,
                    "units": UnitTypesDischarge.cms,
                },
            },
        }
        return deepcopy(_RIVER_DISCHARGE_MODEL)

    def test_validate_RiverDischargeModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        river_model = RiverDischargeModel.model_validate(model)

        # Assert
        assert river_model.base_discharge == UnitfulDischarge(
            10, UnitTypesDischarge.cms
        )
        assert river_model.timeseries.shape_type == ShapeType.constant
        assert river_model.timeseries.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert river_model.timeseries.end_time == UnitfulTime(10, UnitTypesTime.hours)
        assert river_model.timeseries.peak_intensity == UnitfulDischarge(
            11, UnitTypesDischarge.cms
        )

    def test_validate_RiverDischargeModel_valid_input_no_base_discharge(self):
        # Arange
        model = self.get_test_model()
        model.pop("base_discharge")

        # Act
        river_model = RiverDischargeModel.model_validate(model)

        # Assert
        assert river_model.base_discharge == UnitfulDischarge(0, UnitTypesDischarge.cms)
        assert river_model.timeseries.shape_type == ShapeType.constant
        assert river_model.timeseries.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert river_model.timeseries.end_time == UnitfulTime(10, UnitTypesTime.hours)
        assert river_model.timeseries.peak_intensity == UnitfulDischarge(
            11, UnitTypesDischarge.cms
        )


class TestTimeModel:
    @staticmethod
    def get_test_model():
        _TIME_MODEL = {
            # "timing": Timing.idealized.value,
            # "duration_before_t0": {
            #     "value": 10,
            #     "units": UnitTypesTime.hours,
            # },
            # "duration_after_t0": {
            #     "value": 10,
            #     "units": UnitTypesTime.hours,
            # },
            "start_time": "2020-01-01 00:00:00",
            "end_time": "2020-01-03 00:00:00",
        }
        return deepcopy(_TIME_MODEL)

    def test_validate_TimeModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        time_model = TimeModel.model_validate(model)

        # Assert
        # assert time_model.timing == Timing.idealized
        # assert time_model.duration_before_t0 == UnitfulTime(10, UnitTypesTime.hours)
        # assert time_model.duration_after_t0 == UnitfulTime(10, UnitTypesTime.hours)
        assert time_model.start_time == "2020-01-01 00:00:00"
        assert time_model.end_time == "2020-01-03 00:00:00"

    @pytest.mark.skip("currently testing refactor of this feature")
    def test_validate_TimeModel_invalid_input_duration_before_t0_cannot_be_negative(
        self,
    ):
        # Arange
        model = self.get_test_model()
        model["duration_before_t0"]["value"] = -10

        # Act
        with pytest.raises(ValidationError) as e:
            TimeModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0] == "Duration before T0 must be positive"
        )

    @pytest.mark.skip("currently testing refactor of this feature")
    def test_validate_TimeModel_invalid_input_duration_after_t0_cannot_be_negative(
        self,
    ):
        # Arange
        model = self.get_test_model()
        model["duration_after_t0"]["value"] = -10

        # Act
        with pytest.raises(ValidationError) as e:
            TimeModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert errors[0]["ctx"]["error"].args[0] == "Duration after T0 must be positive"

    def test_validate_TimeModel_invalid_input_end_time_before_start_time(
        self,
    ):  # Arange
        model = self.get_test_model()
        model["start_time"] = "2020-01-03 00:00:00"
        model["end_time"] = "2020-01-01 00:00:00"

        # Act
        with pytest.raises(ValidationError) as e:
            TimeModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert errors[0]["ctx"]["error"].args[0] == "Start time must be before end time"

    def test_validate_TimeModel_incorrect_time_format(self):
        # Arange
        model = self.get_test_model()
        incorrect_format = "2020/01/01 00:00:00"
        model["start_time"] = incorrect_format

        # Act
        with pytest.raises(ValidationError) as e:
            TimeModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == f"Time must be in format {DEFAULT_DATETIME_FORMAT}. Got {incorrect_format}"
        )


class TestTideModel:
    @staticmethod
    def get_test_model():
        _TIDE_MODEL = {
            "source": TideSource.timeseries.value,
            "timeseries": TestTimeseriesModel.get_test_model(ShapeType.constant),
        }
        return deepcopy(_TIDE_MODEL)

    def test_validate_TideModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        tide_model = TideModel.model_validate(model)

        # Assert
        assert tide_model.source == TideSource.timeseries
        assert tide_model.timeseries == TimeseriesModel.model_validate(
            TestTimeseriesModel.get_test_model(ShapeType.constant)
        )

    def test_validate_TideModel_invalid_input_timeseries_must_be_set_when_source_is_timeseries(
        self,
    ):
        # Arange
        model = self.get_test_model()
        model.pop("timeseries")

        # Act
        with pytest.raises(ValidationError) as e:
            TideModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "Timeseries Model must be set when source is timeseries"
        )

    @pytest.mark.skip("TideSource.model not implemented")
    def test_validate_TideModel_valid_input_TideSource_model(self):
        pass


class TestSurgeModel:
    @staticmethod
    def get_test_model():
        _SURGE_MODEL = {
            "source": TideSource.timeseries.value,
            "timeseries": TestTimeseriesModel.get_test_model(ShapeType.harmonic),
        }
        return deepcopy(_SURGE_MODEL)

    def test_validate_SurgeModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        surge_model = TideModel.model_validate(model)

        # Assert
        assert surge_model.source == TideSource.timeseries
        assert surge_model.timeseries == TimeseriesModel.model_validate(
            TestTimeseriesModel.get_test_model(ShapeType.harmonic)
        )

    def test_validate_SurgeModel_invalid_input_timeseries_must_be_set_when_source_is_timeseries(
        self,
    ):
        # Arange
        model = self.get_test_model()
        model.pop("timeseries")

        # Act
        with pytest.raises(ValidationError) as e:
            TideModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "Timeseries Model must be set when source is timeseries"
        )

    @pytest.mark.skip("SurgeSource.none not implemented")
    def test_validate_TideModel_valid_input_TideSource_model(self):
        pass


class TestTranslationModel:
    @staticmethod
    def get_test_model():
        _TRANSLATION_MODEL = {
            "eastwest_translation": {"value": 5, "units": UnitTypesLength.miles},
            "northsouth_translation": {"value": 15, "units": UnitTypesLength.miles},
        }
        return deepcopy(_TRANSLATION_MODEL)

    def test_validate_TranslationModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        translation_model = TranslationModel.model_validate(model)

        # Assert
        assert translation_model.eastwest_translation == UnitfulLength(
            5, UnitTypesLength.miles
        )
        assert translation_model.northsouth_translation == UnitfulLength(
            15, UnitTypesLength.miles
        )

    def test_validate_TranslationModel_valid_input_no_translation(self):
        # Arange
        model = {}

        # Act
        translation_model = TranslationModel.model_validate(model)

        # Assert
        assert translation_model.eastwest_translation == UnitfulLength(
            0, UnitTypesLength.miles
        )
        assert translation_model.northsouth_translation == UnitfulLength(
            0, UnitTypesLength.miles
        )


class TestHurricaneModel:
    @staticmethod
    def get_test_model():
        # Arange
        _HURRICANE_MODEL = {
            "track_name": "test_track",
            "hurricane_translation": TestTranslationModel.get_test_model(),
        }
        return deepcopy(_HURRICANE_MODEL)

    def test_validate_HurricaneModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        hurricane_model = HurricaneModel.model_validate(model)

        # Assert
        assert hurricane_model.track_name == "test_track"
        assert hurricane_model.hurricane_translation == TranslationModel.model_validate(
            TestTranslationModel.get_test_model()
        )


class TestOverlandModel:
    @staticmethod
    def get_test_model():
        _OVERLAND_MODEL = {
            "wind": TestWindModel.get_test_model(),
            "river": [
                TestRiverDischargeModel.get_test_model(),
                TestRiverDischargeModel.get_test_model(),
            ],
            "tide": TestTideModel.get_test_model(),
            "surge": TestSurgeModel.get_test_model(),
            "rainfall": TestRainfallModel.get_test_model(),
            "hurricane": TestHurricaneModel.get_test_model(),
        }
        return deepcopy(_OVERLAND_MODEL)

    def test_validate_OverlandModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        overland_model = OverlandModel.model_validate(model)

        # Assert
        assert overland_model.wind == WindModel.model_validate(
            TestWindModel.get_test_model()
        )
        assert overland_model.river == [
            RiverDischargeModel.model_validate(
                TestRiverDischargeModel.get_test_model()
            ),
            RiverDischargeModel.model_validate(
                TestRiverDischargeModel.get_test_model()
            ),
        ]
        assert overland_model.tide == TideModel.model_validate(
            TestTideModel.get_test_model()
        )
        assert overland_model.surge == SurgeModel.model_validate(
            TestSurgeModel.get_test_model()
        )
        assert overland_model.rainfall == RainfallModel.model_validate(
            TestRainfallModel.get_test_model()
        )
        assert overland_model.hurricane == HurricaneModel.model_validate(
            TestHurricaneModel.get_test_model()
        )

    def test_validate_OverlandModel_valid_input_all_is_optional(self):
        # Arange
        model = {}

        # Act
        overland_model = OverlandModel.model_validate(model)

        # Assert
        assert overland_model.wind is None
        assert overland_model.river is None
        assert overland_model.tide is None
        assert overland_model.surge is None
        assert overland_model.rainfall is None
        assert overland_model.hurricane is None


class TestOffShoreModel:
    @staticmethod
    def get_test_model():
        _OFFSHORE_MODEL = {
            "wind": TestWindModel.get_test_model(),
            "tide": TestTideModel.get_test_model(),
            "rainfall": TestRainfallModel.get_test_model(),
            "hurricane": TestHurricaneModel.get_test_model(),
        }
        return deepcopy(_OFFSHORE_MODEL)

    def test_validate_OffShoreModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        offshore_model = OffShoreModel.model_validate(model)

        # Assert
        assert offshore_model.wind == WindModel.model_validate(
            TestWindModel.get_test_model()
        )
        assert offshore_model.tide == TideModel.model_validate(
            TestTideModel.get_test_model()
        )
        assert offshore_model.rainfall == RainfallModel.model_validate(
            TestRainfallModel.get_test_model()
        )
        assert offshore_model.hurricane == HurricaneModel.model_validate(
            TestHurricaneModel.get_test_model()
        )

    def test_validate_OverlandModel_valid_input_all_is_optional(self):
        # Arange
        model = {}

        # Act
        offshore_model = OffShoreModel.model_validate(model)

        # Assert
        assert offshore_model.wind is None
        assert offshore_model.tide is None
        assert offshore_model.rainfall is None
        assert offshore_model.hurricane is None


class TestEventModel:
    @staticmethod
    def get_test_model():
        _EVENT_MODEL = {
            "name": "test_event",
            "mode": "single_event",
            "description": "test_description",
            "time": TestTimeModel.get_test_model(),
            "overland": TestOverlandModel.get_test_model(),
            "offshore": TestOffShoreModel.get_test_model(),
            "water_level_offset": {"value": 2, "units": UnitTypesLength.meters},
        }
        return deepcopy(_EVENT_MODEL)

    def test_validate_EventModel_valid_input(self):
        # Arange
        model = self.get_test_model()

        # Act
        event_model = EventModel.model_validate(model)

        # Assert
        assert event_model.name == "test_event"
        assert event_model.description == "test_description"
        assert event_model.mode == Mode.single_event
        assert event_model.time == TimeModel.model_validate(
            TestTimeModel.get_test_model()
        )

        assert event_model.overland == OverlandModel.model_validate(
            TestOverlandModel.get_test_model()
        )
        assert event_model.offshore == OffShoreModel.model_validate(
            TestOffShoreModel.get_test_model()
        )
        assert event_model.water_level_offset == UnitfulLength(
            2, UnitTypesLength.meters
        )

    def test_validate_EventModel_valid_input_all_optional(self):
        # Arange
        model = self.get_test_model()
        model.pop("description")
        model.pop("overland")
        model.pop("offshore")
        model.pop("water_level_offset")

        # Act
        event_model = EventModel.model_validate(model)

        # Assert
        assert event_model.name == "test_event"
        assert event_model.mode == Mode.single_event
        assert event_model.time == TimeModel.model_validate(
            TestTimeModel.get_test_model()
        )

        assert event_model.description is None
        assert event_model.overland is None
        assert event_model.offshore is None
        assert event_model.water_level_offset == UnitfulLength(
            0, UnitTypesLength.meters
        )


@pytest.mark.skip("TestEventSetModel not implemented")
class TestEventSetModel:
    pass
