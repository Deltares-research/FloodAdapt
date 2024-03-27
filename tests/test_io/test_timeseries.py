import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from flood_adapt.object_model.interface.events import Scstype
from flood_adapt.object_model.io.timeseries import (
    ShapeType,
    Timeseries,
    TimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
)


class TestTimeseriesModel:
    @staticmethod
    def get_model(shape_type: ShapeType):
        _TIMESERIES_MODEL_SIMPLE = {
            "shape_type": ShapeType.constant.value,
            "start_time": {"value": 0, "units": UnitTypesTime.hours},
            "end_time": {"value": 1, "units": UnitTypesTime.hours},
            "peak_intensity": {"value": 1, "units": UnitTypesIntensity.mm_hr},
        }

        _TIMESERIES_MODEL_SCS = {
            "shape_type": ShapeType.scs.value,
            "start_time": {"value": 0, "units": UnitTypesTime.hours},
            "end_time": {"value": 1, "units": UnitTypesTime.hours},
            "cumulative": {"value": 1, "units": UnitTypesLength.millimeters},
            "csv_file_path": "test_scs.csv",
            "scstype": Scstype.type1.value,
        }

        _TIMESERIES_MODEL_CSV_FILE = {
            "shape_type": ShapeType.csv_file.value,
            "start_time": {"value": 0, "units": UnitTypesTime.hours},
            "end_time": {"value": 1, "units": UnitTypesTime.hours},
            "csv_file_path": "test.csv",
        }

        models = {
            ShapeType.constant: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.gaussian: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.triangle: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.harmonic: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.scs: _TIMESERIES_MODEL_SCS,
            ShapeType.csv_file: _TIMESERIES_MODEL_CSV_FILE,
        }
        return models[shape_type]

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
            ShapeType.harmonic,
        ],
    )
    def test_TimeseriesModel_valid_input_simple_shapetypes(self, shape_type):
        # Arange
        model = self.get_model(shape_type)

        # Act
        timeseries_model = TimeseriesModel.model_validate(model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.constant
        assert timeseries_model.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert timeseries_model.end_time == UnitfulTime(1, UnitTypesTime.hours)
        assert timeseries_model.peak_intensity == UnitfulIntensity(
            1, UnitTypesIntensity.mm_hr
        )

    def test_TimeseriesModel_valid_input_scs_shapetype(self, tmp_path):
        # Arange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_model(ShapeType.scs)
        model["csv_file_path"] = Path(temp_file)

        # Act
        timeseries_model = TimeseriesModel.model_validate(model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.scs
        assert timeseries_model.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert timeseries_model.end_time == UnitfulTime(1, UnitTypesTime.hours)
        assert timeseries_model.cumulative == UnitfulLength(
            1, UnitTypesLength.millimeters
        )
        assert timeseries_model.csv_file_path == Path(temp_file)
        assert timeseries_model.scstype == Scstype.type1

    def test_TimeseriesModel_valid_input_csv_shapetype(self, tmp_path):
        # Arange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_model(ShapeType.csv_file)
        model["csv_file_path"] = Path(temp_file)

        # Act
        timeseries_model = TimeseriesModel.model_validate(model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.csv_file
        assert timeseries_model.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert timeseries_model.end_time == UnitfulTime(1, UnitTypesTime.hours)
        assert timeseries_model.csv_file_path == Path(temp_file)

    def test_TimeseriesModel_invalid_input_shapetype_csvfile_not_provided(self):
        # Arange
        model = self.get_model(ShapeType.csv_file)
        model.pop("csv_file_path")

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0]
            == "csvfile must be provided for csv_file timeseries"
        )

    def test_TimeseriesModel_invalid_input_csvfile_wrong_suffix(self):
        # Arange
        model = self.get_model(ShapeType.csv_file)
        model["csv_file_path"] = "test.txt"

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0] == "Timeseries file must be a .csv file"
        )

    def test_TimeseriesModel_invalid_input_csvfile_does_not_exist(self):
        # Arange
        model = self.get_model(ShapeType.csv_file)

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            errors[0]["ctx"]["error"].args[0] == "Timeseries file must be a valid file"
        )

    @pytest.mark.parametrize("to_remove", ["scstype", "csv_file_path", "cumulative"])
    def test_TimeseriesModel_invalid_input_shapetype_scs(self, tmp_path, to_remove):
        # Arange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_model(ShapeType.scs)
        model["csv_file_path"] = Path(temp_file)
        model.pop(to_remove)

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "csvfile, scstype and cumulative must be provided for SCS timeseries:"
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
            ShapeType.harmonic,
        ],
    )
    def test_TimeseriesModel_invalid_input_simple_shapetypes_both_peak_and_cumulative(
        self, shape_type
    ):
        # Arange
        model = self.get_model(shape_type)
        model["peak_intensity"] = {"value": 1, "units": UnitTypesIntensity.mm_hr}
        model["cumulative"] = {"value": 1, "units": UnitTypesLength.millimeters}

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Exactly one of peak_intensity or cumulative must be set"
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
            ShapeType.harmonic,
        ],
    )
    def test_TimeseriesModel_invalid_input_simple_shapetypes_neither_peak_nor_cumulative(
        self, shape_type
    ):
        # Arange
        model = self.get_model(shape_type)
        model.pop("peak_intensity")
        if "cumulative" in model:
            model.pop("cumulative")

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Exactly one of peak_intensity or cumulative must be set"
            in errors[0]["ctx"]["error"].args[0]
        )

    def test_TimeseriesModel_invalid_input_start_time_greater_than_end_time(
        self,
    ):
        # Arange
        model = self.get_model(ShapeType.constant)
        model["start_time"]["value"] = 1
        model["end_time"]["value"] = 0

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Timeseries start time cannot be later than its end time:"
            in errors[0]["ctx"]["error"].args[0]
        )


class TestTimeseries:
    def test_data_property(self):
        model = Timeseries()
        model.attrs = TimeseriesModel(
            shape_type=ShapeType.constant,
            start_time=UnitfulTime(0, UnitTypesTime.hours),
            end_time=UnitfulTime(1, UnitTypesTime.hours),
            peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
        )
        assert model.data is not None

    def test_calculate_data(self):
        model = Timeseries()
        model.attrs = TimeseriesModel(
            shape_type=ShapeType.constant,
            start_time=UnitfulTime(0, UnitTypesTime.hours),
            end_time=UnitfulTime(1, UnitTypesTime.hours),
            peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
        )

        duration = (model.attrs.end_time - model.attrs.start_time).convert(
            UnitTypesTime.seconds
        )
        timestep = UnitfulTime(1, UnitTypesTime.seconds)
        data = model.calculate_data(timestep)

        assert (duration.value / timestep.value) == len(data)
        assert np.amax(data) == model.attrs.peak_intensity.value

    def test_load_file(self):
        fd, path = tempfile.mkstemp(suffix=".toml")
        try:
            with os.fdopen(fd, "w") as tmp:
                # Write to the file
                tmp.write(
                    """
                shape_type = "constant"
                start_time = { value = 0, units = "hours" }
                end_time = { value = 1, units = "hours" }
                peak_intensity = { value = 1, units = "mm/hr" }
                """
                )

            try:
                model = Timeseries.load_file(path)
            except Exception as e:
                pytest.fail(str(e))

            assert model.attrs.shape_type == ShapeType.constant
            assert model.attrs.start_time == UnitfulTime(0, UnitTypesTime.hours)
            assert model.attrs.end_time == UnitfulTime(1, UnitTypesTime.hours)
            assert model.attrs.peak_intensity == UnitfulIntensity(
                1, UnitTypesIntensity.mm_hr
            )

        finally:
            os.remove(path)

    def test_save(self):
        try:
            ts = Timeseries()
            temp_path = "test.toml"
            ts.attrs = TimeseriesModel(
                shape_type=ShapeType.constant,
                start_time=UnitfulTime(0, UnitTypesTime.hours),
                end_time=UnitfulTime(1, UnitTypesTime.hours),
                peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
            )
            try:
                ts.save(temp_path)
            except Exception as e:
                pytest.fail(str(e))

            assert os.path.exists(temp_path)

        finally:
            os.remove(temp_path)

    def test_to_dataframe(self):
        # Create a Timeseries object
        ts = Timeseries().load_dict(
            {
                "shape_type": "constant",
                "start_time": {"value": 0, "units": "hours"},
                "end_time": {"value": 1, "units": "hours"},
                "peak_intensity": {"value": 1, "units": "mm/hr"},
            }
        )

        # Call the to_dataframe method
        df = ts.to_dataframe(UnitfulTime(10, UnitTypesTime.seconds))

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["intensity"]
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_data = ts.calculate_data(
            time_step=UnitfulTime(10, UnitTypesTime.seconds)
        )
        expected_time_range = pd.date_range(
            start=pd.Timestamp("00:00:00"), periods=len(expected_data), freq="10S"
        )
        expected_df = pd.DataFrame(
            expected_data, columns=["intensity"], index=expected_time_range
        )
        expected_df.index.name = "time"

        pd.testing.assert_frame_equal(df, expected_df)


# class TestCompositeTimeseries:
#     TIMESERIES_SHAPES = [
#         ShapeType.constant,
#         ShapeType.gaussian,
#         ShapeType.triangle,
#         ShapeType.scs,
#     ]
#     TIMESERIES_TIME_UNITS = [
#         UnitTypesTime.minutes,
#         UnitTypesTime.hours,
#         UnitTypesTime.days,
#     ]
#     TIMESERIES_INTENSITY_UNITS = [UnitTypesIntensity.mm_hr, UnitTypesIntensity.inch_hr]
#     TIME_START_VALUES = [0, 5, 10]
#     TIME_END_VALUES = [13, 16]
#     INTENSITY_VALUES = [3, 7]
#     TIME_STEP_VALUES = [
#         UnitfulTime(1, UnitTypesTime.seconds),
#         UnitfulTime(10, UnitTypesTime.minutes),
#     ]

#     # Generate all combinations of the above parameters
#     params = list(
#         product(
#             TIMESERIES_SHAPES,
#             TIMESERIES_TIME_UNITS,
#             TIMESERIES_INTENSITY_UNITS,
#             TIME_START_VALUES,
#             TIME_END_VALUES,
#             INTENSITY_VALUES,
#             TIME_STEP_VALUES,
#         )
#     )
#     params_reversed = params[:][::-1]
#     params_pairs = list(zip(params, params_reversed))

#     def _make_timeseries(
#         self, shape_type, start, end, peak, time_units, intensity_unit, time_step
#     ):
#         dct = {
#             "shape_type": shape_type,
#             "start_time": UnitfulTime(start, time_units),
#             "end_time": UnitfulTime(end, time_units),
#             "peak_intensity": UnitfulIntensity(peak, intensity_unit),
#             "time_step": time_step,
#         }
#         test_series = Timeseries.load_dict(dct)
#         return test_series

#     @pytest.mark.parametrize("testcase1, testcase2", params_pairs)
#     def test_composite_timeseries_add_timeseries(self, testcase1, testcase2):
#         # (shape1, time_unit1, intensity_unit1, time_start_value1, time_end_value1, intensity_value1), (shape2, time_unit2, intensity_unit2, time_start_value2, time_end_value2, intensity_value2) = param_pair
#         (
#             shape1,
#             time_unit1,
#             intensity_unit1,
#             time_start_value1,
#             time_end_value1,
#             intensity_value1,
#             time_step1,
#         ) = testcase1
#         (
#             shape2,
#             time_unit2,
#             intensity_unit2,
#             time_start_value2,
#             time_end_value2,
#             intensity_value2,
#             time_step2,
#         ) = testcase2

#         ts1 = self._make_timeseries(
#             shape_type=shape1,
#             start=time_start_value1,
#             end=time_end_value1,
#             peak=intensity_value1,
#             time_units=time_unit1,
#             intensity_unit=intensity_unit1,
#             time_step=time_step1,
#         )
#         ts2 = self._make_timeseries(
#             shape_type=shape2,
#             start=time_start_value2,
#             end=time_end_value2,
#             peak=intensity_value2,
#             time_units=time_unit2,
#             intensity_unit=intensity_unit2,
#             time_step=time_step2,
#         )

#         composite = CompositeTimeseries(
#             timeseries_list=[ts1, ts2],
#             intensity_unit=UnitTypesIntensity.mm_hr,
#             time_unit=UnitTypesTime.hours,
#         )

#         expected_start = min(ts1.attrs.start_time, ts2.attrs.start_time)
#         expected_end = max(ts1.attrs.end_time, ts2.attrs.end_time)

#         max1 = ts1.attrs.peak_intensity.convert(UnitTypesIntensity.mm_hr)
#         max2 = ts2.attrs.peak_intensity.convert(UnitTypesIntensity.mm_hr)

#         min_expected_peak = max(max1, max2)  # no overlap at all
#         max_expected_peak = max1 + max2  # perfect overlap
#         assert composite.start_time == expected_start
#         assert composite.end_time == expected_end

#         if not min_expected_peak <= composite.peak_intensity:
#             print(
#                 f"min_expected_peak: {min_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {min_expected_peak <= composite.peak_intensity}"
#             )
#             composite.plot()
#         assert (
#             min_expected_peak <= composite.peak_intensity
#         ), f"min_expected_peak: {min_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {min_expected_peak <= composite.peak_intensity}"
#         assert (
#             composite.peak_intensity <= max_expected_peak
#         ), f"max_expected_peak: {max_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {composite.peak_intensity <= max_expected_peak}"

#     @pytest.mark.parametrize("timestep", TIME_STEP_VALUES)
#     def test_timeseries_calculate_data_timesteps(self, timestep):
#         dct = {
#             "shape_type": ShapeType.constant,
#             "start_time": UnitfulTime(0, UnitTypesTime.hours),
#             "end_time": UnitfulTime(1, UnitTypesTime.hours),
#             "peak_intensity": UnitfulIntensity(1, UnitTypesIntensity.inch_hr),
#             "time_step": timestep,
#         }
#         test_series = Timeseries.load_dict(dct)

#         _time_step = timestep.convert(UnitTypesTime.seconds)
#         _duration = (test_series.attrs.end_time - test_series.attrs.start_time).convert(
#             UnitTypesTime.seconds
#         )
#         _data = test_series.calculate_data(timestep)

#         assert (
#             len(_data) == _duration.value / _time_step.value
#         ), f"Timeseries data length does not match expected length: {len(_data)}, {_duration.value / _time_step.value}"


if __name__ == "__main__":
    pass
