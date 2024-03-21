import os
import tempfile
from itertools import product

import numpy as np
import pytest

from flood_adapt.object_model.io.timeseries import (
    CompositeTimeseries,
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
    def test_validate_peak_intensity(self):
        with pytest.raises(ValueError, match="Intensity cannot be negative"):
            TimeseriesModel(
                shape_type=ShapeType.block,
                start_time=UnitfulTime(0, UnitTypesTime.hours),
                end_time=UnitfulTime(1, UnitTypesTime.hours),
                peak_intensity=UnitfulIntensity(-1, UnitTypesIntensity.mm_hr),
            )

    def test_validate_cumulative(self):
        with pytest.raises(ValueError, match="Length cannot be negative"):
            TimeseriesModel(
                shape_type=ShapeType.block,
                start_time=UnitfulTime(0, UnitTypesTime.hours),
                end_time=UnitfulTime(1, UnitTypesTime.hours),
                cumulative=UnitfulLength(-1, UnitTypesLength.millimeters),
            )

    def test_validate_timeseries_model_start_time_greater_than_end_time(self):
        with pytest.raises(
            ValueError, match="Timeseries start time cannot be later than its end time"
        ):
            TimeseriesModel(
                shape_type=ShapeType.block,
                start_time=UnitfulTime(1, UnitTypesTime.hours),
                end_time=UnitfulTime(0, UnitTypesTime.hours),
            )

    def test_validate_timeseries_model_both_cumulative_and_peak_intensity_set(self):
        with pytest.raises(
            ValueError, match="Exactly one of peak_intensity or cumulative must be set"
        ):
            TimeseriesModel(
                shape_type=ShapeType.block,
                start_time=UnitfulTime(0, UnitTypesTime.hours),
                end_time=UnitfulTime(1, UnitTypesTime.hours),
                peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
                cumulative=UnitfulLength(1, UnitTypesLength.millimeters),
            )

    def test_validate_timeseries_model_neither_cumulative_nor_peak_intensity_set(self):
        with pytest.raises(
            ValueError, match="Exactly one of peak_intensity or cumulative must be set"
        ):
            TimeseriesModel(
                shape_type=ShapeType.block,
                start_time=UnitfulTime(0, UnitTypesTime.hours),
                end_time=UnitfulTime(1, UnitTypesTime.hours),
            )


class TestTimeseries:
    def test_data_property(self):
        model = Timeseries()
        model.attrs = TimeseriesModel(
            shape_type=ShapeType.block,
            start_time=UnitfulTime(0, UnitTypesTime.hours),
            end_time=UnitfulTime(1, UnitTypesTime.hours),
            peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
        )
        assert model.data is not None

    def test_calculate_data(self):
        model = Timeseries()
        model.attrs = TimeseriesModel(
            shape_type=ShapeType.block,
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
                shape_type = "block"
                start_time = { value = 0, units = "hours" }
                end_time = { value = 1, units = "hours" }
                peak_intensity = { value = 1, units = "mm/hr" }
                """
                )

            try:
                model = Timeseries.load_file(path)
            except Exception as e:
                pytest.fail(str(e))

            assert model.attrs.shape_type == ShapeType.block
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
                shape_type=ShapeType.block,
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


class TestCompositeTimeseries:
    TIMESERIES_SHAPES = [
        ShapeType.block,
        ShapeType.gaussian,
        ShapeType.triangle,
        ShapeType.scs,
    ]
    TIMESERIES_TIME_UNITS = [
        UnitTypesTime.minutes,
        UnitTypesTime.hours,
        UnitTypesTime.days,
    ]
    TIMESERIES_INTENSITY_UNITS = [UnitTypesIntensity.mm_hr, UnitTypesIntensity.inch_hr]
    TIME_START_VALUES = [0, 5, 10]
    TIME_END_VALUES = [13, 16]
    INTENSITY_VALUES = [3, 7]
    TIME_STEP_VALUES = [
        UnitfulTime(1, UnitTypesTime.seconds),
        UnitfulTime(10, UnitTypesTime.minutes),
    ]

    # Generate all combinations of the above parameters
    params = list(
        product(
            TIMESERIES_SHAPES,
            TIMESERIES_TIME_UNITS,
            TIMESERIES_INTENSITY_UNITS,
            TIME_START_VALUES,
            TIME_END_VALUES,
            INTENSITY_VALUES,
            TIME_STEP_VALUES,
        )
    )
    params_reversed = params[:][::-1]
    params_pairs = list(zip(params, params_reversed))

    def _make_timeseries(
        self, shape_type, start, end, peak, time_units, intensity_unit, time_step
    ):
        dct = {
            "shape_type": shape_type,
            "start_time": UnitfulTime(start, time_units),
            "end_time": UnitfulTime(end, time_units),
            "peak_intensity": UnitfulIntensity(peak, intensity_unit),
            "time_step": time_step,
        }
        test_series = Timeseries.load_dict(dct)
        return test_series

    @pytest.mark.parametrize("testcase1, testcase2", params_pairs)
    def test_composite_timeseries_add_timeseries(self, testcase1, testcase2):
        # (shape1, time_unit1, intensity_unit1, time_start_value1, time_end_value1, intensity_value1), (shape2, time_unit2, intensity_unit2, time_start_value2, time_end_value2, intensity_value2) = param_pair
        (
            shape1,
            time_unit1,
            intensity_unit1,
            time_start_value1,
            time_end_value1,
            intensity_value1,
            time_step1,
        ) = testcase1
        (
            shape2,
            time_unit2,
            intensity_unit2,
            time_start_value2,
            time_end_value2,
            intensity_value2,
            time_step2,
        ) = testcase2

        ts1 = self._make_timeseries(
            shape_type=shape1,
            start=time_start_value1,
            end=time_end_value1,
            peak=intensity_value1,
            time_units=time_unit1,
            intensity_unit=intensity_unit1,
            time_step=time_step1,
        )
        ts2 = self._make_timeseries(
            shape_type=shape2,
            start=time_start_value2,
            end=time_end_value2,
            peak=intensity_value2,
            time_units=time_unit2,
            intensity_unit=intensity_unit2,
            time_step=time_step2,
        )

        composite = CompositeTimeseries(
            timeseries_list=[ts1, ts2],
            intensity_unit=UnitTypesIntensity.mm_hr,
            time_unit=UnitTypesTime.hours,
        )

        expected_start = min(ts1.attrs.start_time, ts2.attrs.start_time)
        expected_end = max(ts1.attrs.end_time, ts2.attrs.end_time)

        max1 = ts1.attrs.peak_intensity.convert(UnitTypesIntensity.mm_hr)
        max2 = ts2.attrs.peak_intensity.convert(UnitTypesIntensity.mm_hr)

        min_expected_peak = max(max1, max2)  # no overlap at all
        max_expected_peak = max1 + max2  # perfect overlap
        assert composite.start_time == expected_start
        assert composite.end_time == expected_end

        if not min_expected_peak <= composite.peak_intensity:
            print(
                f"min_expected_peak: {min_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {min_expected_peak <= composite.peak_intensity}"
            )
            composite.plot()
        assert (
            min_expected_peak <= composite.peak_intensity
        ), f"min_expected_peak: {min_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {min_expected_peak <= composite.peak_intensity}"
        assert (
            composite.peak_intensity <= max_expected_peak
        ), f"max_expected_peak: {max_expected_peak.convert(composite.peak_intensity.units)}, composite.peak_intensity: {composite.peak_intensity}, {composite.peak_intensity <= max_expected_peak}"

    @pytest.mark.parametrize("timestep", TIME_STEP_VALUES)
    def test_timeseries_calculate_data_timesteps(self, timestep):
        dct = {
            "shape_type": ShapeType.block,
            "start_time": UnitfulTime(0, UnitTypesTime.hours),
            "end_time": UnitfulTime(1, UnitTypesTime.hours),
            "peak_intensity": UnitfulIntensity(1, UnitTypesIntensity.inch_hr),
            "time_step": timestep,
        }
        test_series = Timeseries.load_dict(dct)

        _time_step = timestep.convert(UnitTypesTime.seconds)
        _duration = (test_series.attrs.end_time - test_series.attrs.start_time).convert(
            UnitTypesTime.seconds
        )
        _data = test_series.calculate_data(timestep)

        assert (
            len(_data) == _duration.value / _time_step.value
        ), f"Timeseries data length does not match expected length: {len(_data)}, {_duration.value / _time_step.value}"


if __name__ == "__main__":
    pass
