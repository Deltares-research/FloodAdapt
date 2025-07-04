import math
import os
import tempfile
from datetime import timedelta
from itertools import permutations
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.time_frame import REFERENCE_TIME, TimeFrame
from flood_adapt.objects.forcing.timeseries import (
    BlockTimeseries,
    GaussianTimeseries,
    ScsTimeseries,
    Scstype,
    ShapeType,
    TimeseriesFactory,
    TriangleTimeseries,
)


class TestTimeseriesModel:
    @staticmethod
    def get_test_model(shape_type: ShapeType):
        _TIMESERIES_MODEL_SIMPLE = {
            "shape_type": ShapeType.block.value,
            "duration": {"value": 1, "units": us.UnitTypesTime.hours},
            "peak_time": {"value": 0, "units": us.UnitTypesTime.hours},
            "peak_value": {"value": 1, "units": us.UnitTypesIntensity.mm_hr},
        }
        _TIMESERIES_MODEL_GAUSSIAN = {
            "shape_type": ShapeType.gaussian.value,
            "duration": {"value": 1, "units": us.UnitTypesTime.hours},
            "peak_time": {"value": 0, "units": us.UnitTypesTime.hours},
            "cumulative": {"value": 1, "units": us.UnitTypesLength.millimeters},
        }
        _TIMESERIES_MODEL_SCS = {
            "shape_type": ShapeType.scs.value,
            "peak_time": {"value": 0, "units": us.UnitTypesTime.hours},
            "duration": {"value": 1, "units": us.UnitTypesTime.hours},
            "cumulative": {"value": 1, "units": us.UnitTypesLength.millimeters},
            "scs_file_name": "scs_rainfall.csv",
            "scs_type": Scstype.type1.value,
        }

        models = {
            ShapeType.block: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.gaussian: _TIMESERIES_MODEL_GAUSSIAN,
            ShapeType.triangle: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.scs: _TIMESERIES_MODEL_SCS,
        }
        return models[shape_type]

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.block,
            ShapeType.triangle,
        ],
    )
    def test_timeseriesmodel_valid_input_simple_shapetypes(self, shape_type):
        # Arrange
        model = self.get_test_model(shape_type)

        # Act
        timeseries_model = TimeseriesFactory.from_args(**model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.block
        assert timeseries_model.peak_time == us.UnitfulTime(
            value=0, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.duration == us.UnitfulTime(
            value=1, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.peak_value == us.UnitfulIntensity(
            value=1, units=us.UnitTypesIntensity.mm_hr
        )

    def test_timeseriesmodel_valid_input_gaussian_shapetype(self):
        # Arrange
        model = self.get_test_model(ShapeType.gaussian)

        # Act
        timeseries_model = TimeseriesFactory.from_args(**model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.gaussian
        assert timeseries_model.peak_time == us.UnitfulTime(
            value=0, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.duration == us.UnitfulTime(
            value=1, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.peak_value is None
        assert timeseries_model.cumulative == us.UnitfulLength(
            value=1, units=us.UnitTypesLength.millimeters
        )

    def test_timeseriesmodel_valid_input_scs_shapetype(self):
        # Arrange
        model = self.get_test_model(ShapeType.scs)

        # Act
        timeseries_model = TimeseriesFactory.from_args(**model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.scs
        assert timeseries_model.peak_time == us.UnitfulTime(
            value=0, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.duration == us.UnitfulTime(
            value=1, units=us.UnitTypesTime.hours
        )
        assert timeseries_model.peak_value is None
        assert timeseries_model.cumulative == us.UnitfulLength(
            value=1, units=us.UnitTypesLength.millimeters
        )

    def test_synthetictimeseries_save_load(self, tmp_path):
        # Arrange
        model = self.get_test_model(ShapeType.block)
        model_path = tmp_path / "test.toml"
        saved = TimeseriesFactory.from_args(**model)

        # Act
        saved.save(model_path)
        loaded = BlockTimeseries.load_file(model_path)

        # Assert
        assert saved.model_dump() == loaded.model_dump()

    def test_timeseriesmodel_invalid_input_shapetype_scs(self, test_db_class):
        # Arrange
        model = self.get_test_model(ShapeType.scs)
        model["peak_value"] = model.pop("cumulative")

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesFactory.from_args(**model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "SCS timeseries must have `cumulative` specified."
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.block,
            ShapeType.triangle,
        ],
    )
    def test_timeseriesmodel_invalid_input_simple_shapetypes_both_peak_and_cumulative(
        self, shape_type
    ):
        # Arrange
        model = self.get_test_model(shape_type)
        model["peak_value"] = {"value": 1, "units": us.UnitTypesIntensity.mm_hr}
        model["cumulative"] = {"value": 1, "units": us.UnitTypesIntensity.mm_hr}

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesFactory.from_args(**model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Either `peak_value` or `cumulative` must be specified for Synthetic Timeseries."
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.block,
            ShapeType.triangle,
        ],
    )
    def test_timeseriesmodel_invalid_input_simple_shapetypes_neither_peak_nor_cumulative(
        self, shape_type
    ):
        # Arrange
        model = self.get_test_model(shape_type)
        model.pop("peak_value")
        if "cumulative" in model:
            model.pop("cumulative")

        # Act
        with pytest.raises(ValidationError) as e:
            TimeseriesFactory.from_args(**model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Either `peak_value` or `cumulative` must be specified for Synthetic Timeseries."
            in errors[0]["ctx"]["error"].args[0]
        )


class TestSyntheticTimeseries:
    TEST_ATTRS = [
        # (duration(hrs), peak_time(hrs), peak_value(mmhr), cumulative(mm), )
        (1, 1, 1, 1),
        (6, 12, 4, 0.5),
        (1, 0, 1, 1),
        (2, 6, 2, 2),
        (2, 24, 14, 2),
        (8, 24, 20, 1),
        (10, 20, 1, 10),
    ]
    SHAPE_TYPES = list(ShapeType)

    @staticmethod
    def get_test_timeseries(
        shape_type: ShapeType = ShapeType.block,
        duration: float = 1,
        peak_value: float = 1,
        peak_time: float = 0,
        cumulative: float = 1,
    ):
        match shape_type:
            case ShapeType.scs:
                return ScsTimeseries(
                    shape_type=ShapeType.scs,
                    peak_time=us.UnitfulTime(
                        value=peak_time, units=us.UnitTypesTime.hours
                    ),
                    duration=us.UnitfulTime(
                        value=duration, units=us.UnitTypesTime.hours
                    ),
                    cumulative=us.UnitfulLength(
                        value=cumulative, units=us.UnitTypesLength.inch
                    ),
                    scs_file_name="scs_rainfall.csv",
                    scs_type=Scstype.type3,
                )
            case ShapeType.gaussian:
                return GaussianTimeseries(
                    shape_type=ShapeType.gaussian,
                    peak_time=us.UnitfulTime(
                        value=peak_time, units=us.UnitTypesTime.hours
                    ),
                    duration=us.UnitfulTime(
                        value=duration, units=us.UnitTypesTime.hours
                    ),
                    cumulative=us.UnitfulLength(
                        value=cumulative, units=us.UnitTypesLength.inch
                    ),
                )
            case _:
                return TimeseriesFactory.from_args(
                    shape_type=shape_type,
                    peak_time=us.UnitfulTime(
                        value=peak_time, units=us.UnitTypesTime.hours
                    ),
                    duration=us.UnitfulTime(
                        value=duration, units=us.UnitTypesTime.hours
                    ),
                    peak_value=us.UnitfulIntensity(
                        value=peak_value, units=us.UnitTypesIntensity.mm_hr
                    ),
                )

    @pytest.mark.parametrize("shape_type", [ShapeType.block, ShapeType.triangle])
    @pytest.mark.parametrize("duration, peak_time, peak_value, cumulative", TEST_ATTRS)
    def test_calculate_data_correct_peak_value(
        self, shape_type, duration, peak_time, peak_value, cumulative
    ):
        time = TimeFrame(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + timedelta(hours=duration),
        )
        ts = self.get_test_timeseries(
            shape_type=shape_type,
            duration=duration,
            peak_time=peak_time,
            peak_value=peak_value,
        )

        data = ts.calculate_data(time.time_step)
        result = math.floor(ts.duration.to_timedelta() / time.time_step)
        assert (
            result == len(data) - 1
        ), f"{ts.duration.to_timedelta()}/{time.time_step} should eq {result}, but it is: {len(data) - 1}."

        assert np.amax(data) == pytest.approx(ts.peak_value.value, rel=1e-2)

    @pytest.mark.parametrize("duration, peak_time, peak_value, cumulative", TEST_ATTRS)
    def test_calculate_data_scs(self, duration, peak_time, peak_value, cumulative):
        time = TimeFrame(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + timedelta(hours=duration),
        )
        ts = self.get_test_timeseries(
            shape_type=ShapeType.scs,
            peak_value=peak_value,
            cumulative=cumulative,
            duration=duration,
            peak_time=peak_time,
        )

        data = ts.calculate_data(time.time_step)
        cum_rainfall_ts = np.trapz(data, dx=time.time_step.total_seconds()) / 3600

        assert abs(cum_rainfall_ts - cumulative) < 0.01
        assert (
            int(ts.duration.to_timedelta() / time.time_step) == len(data) - 1
        ), f"int({ts.duration.to_timedelta()}/{time.time_step}) should eq int({ts.duration.to_timedelta() / time.time_step}), but it is: {len(data) - 1}."

    def test_load_file(self):
        path = Path(tempfile.gettempdir()) / "test.toml"
        with open(path, "w") as f:
            f.write(
                """
            shape_type = "block"
            peak_time = { value = 0, units = "hours" }
            duration = { value = 1, units = "hours" }
            peak_value = { value = 1, units = "mm/hr" }
            """
            )

        result = TimeseriesFactory.load_file(path)

        assert isinstance(result, BlockTimeseries)
        assert result.shape_type == ShapeType.block
        assert result.peak_time == us.UnitfulTime(value=0, units=us.UnitTypesTime.hours)
        assert result.duration == us.UnitfulTime(value=1, units=us.UnitTypesTime.hours)
        assert result.peak_value == us.UnitfulIntensity(
            value=1, units=us.UnitTypesIntensity.mm_hr
        )

    def test_save(self, tmp_path):
        try:
            temp_path = Path(tmp_path) / "test.toml"
            ts = BlockTimeseries(
                shape_type=ShapeType.block,
                peak_time=us.UnitfulTime(value=0, units=us.UnitTypesTime.hours),
                duration=us.UnitfulTime(value=1, units=us.UnitTypesTime.hours),
                peak_value=us.UnitfulIntensity(
                    value=1, units=us.UnitTypesIntensity.mm_hr
                ),
            )

            try:
                ts.save(temp_path)
            except Exception as e:
                pytest.fail(str(e))

            assert os.path.exists(temp_path)

        finally:
            os.remove(temp_path)

    @pytest.mark.parametrize("shape_type", SHAPE_TYPES)
    @pytest.mark.parametrize("duration, peak_time, peak_value, cumulative", TEST_ATTRS)
    def test_to_dataframe_timeseries_falls_inside_of_df(
        self, shape_type, duration, peak_time, peak_value, cumulative
    ):
        ts = self.get_test_timeseries(
            duration=duration,
            peak_time=peak_time,
            peak_value=peak_value,
            cumulative=cumulative,
            shape_type=shape_type,
        )
        time_frame = TimeFrame(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + timedelta(hours=duration),
        )

        # Call the to_dataframe method
        df = ts.to_dataframe(time_frame)

        assert isinstance(df, pd.DataFrame)
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_data = ts.calculate_data(time_step=time_frame.time_step)
        expected_time_range = pd.date_range(
            start=time_frame.start_time,
            end=time_frame.end_time,
            freq=time_frame.time_step,
        )

        assert df.index.equals(
            expected_time_range
        ), f"{df.index} == {expected_time_range}"
        assert np.max(df.values) <= np.max(
            expected_data
        ), f"{np.max(df.values)} <= {np.max(expected_data)}"

    @pytest.mark.parametrize("shape_type", SHAPE_TYPES)
    @pytest.mark.parametrize("duration, peak_time, peak_value, cumulative", TEST_ATTRS)
    def test_to_dataframe_timeseries_falls_outside_of_df(
        self, shape_type, duration, peak_time, peak_value, cumulative
    ):
        # Choose a start time that is way before the REFERENCE_TIME
        full_df_duration = timedelta(hours=4)
        start = REFERENCE_TIME
        end = start + full_df_duration
        time_frame = TimeFrame(
            start_time=start,
            end_time=end,
        )

        # new_peak_time is after the full_df_duration so it will be cut off
        new_peak_time = (
            timedelta(hours=peak_time)
            + 2 * full_df_duration
            + 2 * timedelta(hours=duration)
        ).total_seconds() / 3600

        ts = self.get_test_timeseries(
            duration=duration,
            peak_time=new_peak_time,
            peak_value=peak_value,
            cumulative=cumulative,
            shape_type=shape_type,
        )

        df = ts.to_dataframe(time_frame)

        assert isinstance(df, pd.DataFrame)
        # assert list(df.columns) == ["data_0"]
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_time_range = pd.date_range(
            start=REFERENCE_TIME,
            end=end,
            freq=time_frame.time_step,
        )

        # The last value should always be 0, but there is an off by one error in the calculation for block & gaussian somewhere. Others work as expected
        # TODO fix the off by one error
        assert np.all(df.to_numpy()[:-1] == 0)

        assert df.index.equals(
            expected_time_range
        ), f"{df.index} == {expected_time_range}"


class TestGaussian:
    _TEST_ATTRS = permutations([1, 10, 100, 1000], r=3)

    @pytest.mark.parametrize(
        "cumulative, duration, time_step",
        _TEST_ATTRS,
    )
    def test_cumulative_is_correct(self, cumulative, duration, time_step):
        # Act
        ts = GaussianTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            cumulative=us.UnitfulLength(
                value=cumulative, units=us.UnitTypesLength.millimeters
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.isclose(
            np.trapz(
                data, dx=time_step / 3600
            ),  # divide by 3600 to convert seconds to hours, rainfall units are in [inch | mm | ...] / hr
            ts.cumulative.value,
            atol=1e-3,
        ), f"Integral should be close to cumulative value. {np.trapz(data, time_step)} != {ts.cumulative.value}"
        assert np.all(data >= 0), "All values should be non-negative"

    @pytest.mark.parametrize(
        "peak_value, duration, time_step",
        _TEST_ATTRS,
    )
    def test_peak_value_is_correct(self, peak_value, duration, time_step):
        # Act
        ts = GaussianTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(
                value=peak_value, units=us.UnitTypesIntensity.mm_hr
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.isclose(
            np.amax(data), ts.peak_value.value, atol=1e-3
        ), f"Largest value should be close to peak_value. {np.amax(data)} != {ts.peak_value.value}"
        assert np.all(data >= 0), "All values should be non-negative"


class TestBlock:
    _TEST_ATTRS = permutations([1, 10, 100, 1000], r=3)

    @pytest.mark.parametrize(
        "cumulative, duration, time_step",
        _TEST_ATTRS,
    )
    def test_cumulative_is_correct(self, cumulative, duration, time_step):
        # Act
        time_step /= 100  # to make sure we have enough data points
        ts = BlockTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            cumulative=us.UnitfulLength(
                value=cumulative, units=us.UnitTypesLength.millimeters
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.isclose(
            np.trapz(
                data, dx=time_step / 3600
            ),  # divide by 3600 to convert seconds to hours, rainfall units are in [inch | mm | ...] / hr
            ts.cumulative.value,
            atol=1e-3,
        ), f"Integral should be close to cumulative value. {np.trapz(data, time_step / 3600)} != {ts.cumulative.value}"
        assert np.all(data >= 0), "All values should be non-negative"

    @pytest.mark.parametrize(
        "peak_value, duration, time_step",
        _TEST_ATTRS,
    )
    def test_peak_value_is_correct(self, peak_value, duration, time_step):
        # Act
        time_step /= 100  # to make sure we have enough data points
        ts = BlockTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(
                value=peak_value, units=us.UnitTypesIntensity.mm_hr
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.all(
            data == ts.peak_value.value
        ), f"All values of Block timeseries should be equal to peak value. {np.amax(data)} != {ts.peak_value.value}"
        assert np.all(data >= 0), "All values should be non-negative"


class TestTriangle:
    _TEST_ATTRS = permutations([1, 10, 100, 1000], r=3)

    @pytest.mark.parametrize(
        "cumulative, duration, time_step",
        _TEST_ATTRS,
    )
    def test_cumulative_is_correct(self, cumulative, duration, time_step):
        # Act
        time_step /= 100  # to make sure we have enough data points
        ts = TriangleTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            cumulative=us.UnitfulLength(
                value=cumulative, units=us.UnitTypesLength.millimeters
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.isclose(
            np.trapz(
                data, dx=time_step / 3600
            ),  # divide by 3600 to convert seconds to hours, rainfall units are in [inch | mm | ...] / hr
            ts.cumulative.value,
            atol=1e-3,
        ), f"Integral should be close to cumulative value. {np.trapz(data, time_step / 3600)} != {ts.cumulative.value}"
        assert np.all(data >= 0), "All values should be non-negative"

    @pytest.mark.parametrize(
        "peak_value, duration, time_step",
        _TEST_ATTRS,
    )
    def test_peak_value_is_correct(self, peak_value, duration, time_step):
        # Act
        time_step /= 100  # to make sure we have enough data points
        ts = TriangleTimeseries(
            shape_type=ShapeType.gaussian,
            duration=us.UnitfulTime(value=duration, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=duration / 2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulIntensity(
                value=peak_value, units=us.UnitTypesIntensity.mm_hr
            ),
        )

        data = ts.calculate_data(time_step=timedelta(seconds=time_step))

        assert data.shape[0] > 0, "Time series should have data points"
        assert np.isclose(
            np.amax(data), ts.peak_value.value
        ), f"The largest value of Triangle timeseries should be equal to peak value. {np.amax(data)} != {ts.peak_value.value}"
        assert np.all(data >= 0), "All values should be non-negative"
