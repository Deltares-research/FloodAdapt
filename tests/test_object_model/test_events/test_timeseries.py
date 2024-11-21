import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from flood_adapt.object_model.hazard.event.timeseries import (
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.hazard.interface.models import REFERENCE_TIME, Scstype
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
    def get_test_model(shape_type: ShapeType):
        _TIMESERIES_MODEL_SIMPLE = {
            "shape_type": ShapeType.constant.value,
            "duration": {"value": 1, "units": UnitTypesTime.hours},
            "peak_time": {"value": 0, "units": UnitTypesTime.hours},
            "peak_value": {"value": 1, "units": UnitTypesIntensity.mm_hr},
        }
        _TIMESERIES_MODEL_SCS = {
            "shape_type": ShapeType.scs.value,
            "peak_time": {"value": 0, "units": UnitTypesTime.hours},
            "duration": {"value": 1, "units": UnitTypesTime.hours},
            "cumulative": {"value": 1, "units": UnitTypesLength.millimeters},
            "scs_file_name": "scs_rainfall.csv",
            "scs_type": Scstype.type1.value,
        }

        models = {
            ShapeType.constant: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.gaussian: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.triangle: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.scs: _TIMESERIES_MODEL_SCS,
        }
        return models[shape_type]

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
            ShapeType.scs,
        ],
    )
    def test_TimeseriesModel_valid_input_simple_shapetypes(self, shape_type):
        # Arrange
        model = self.get_test_model(shape_type)

        # Act
        timeseries_model = SyntheticTimeseriesModel.model_validate(model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.constant
        assert timeseries_model.peak_time == UnitfulTime(
            value=0, units=UnitTypesTime.hours
        )
        assert timeseries_model.duration == UnitfulTime(
            value=1, units=UnitTypesTime.hours
        )
        assert timeseries_model.peak_value == UnitfulIntensity(
            value=1, units=UnitTypesIntensity.mm_hr
        )

    def test_SyntheticTimeseries_save_load(self, tmp_path):
        # Arrange
        model = self.get_test_model(ShapeType.constant)
        model_path = tmp_path / "test.toml"
        timeseries = SyntheticTimeseries.load_dict(model)

        # Act
        timeseries.save(model_path)
        loaded_model = SyntheticTimeseries.load_file(model_path)

        # Assert
        assert timeseries == loaded_model

    @pytest.mark.parametrize("to_remove", ["scs_type", "scs_file_name"])
    def test_TimeseriesModel_invalid_input_shapetype_scs(self, to_remove):
        # Arrange
        model = self.get_test_model(ShapeType.scs)
        model.pop(to_remove)

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "SCS timeseries must have scs_file_name, scs_type and cumulative specified."
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
        ],
    )
    def test_TimeseriesModel_invalid_input_simple_shapetypes_both_peak_and_cumulative(
        self, shape_type
    ):
        # Arrange
        model = self.get_test_model(shape_type)
        model["peak_value"] = {"value": 1, "units": UnitTypesIntensity.mm_hr}
        model["cumulative"] = {"value": 1, "units": UnitTypesLength.millimeters}

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Either peak_value or cumulative must be specified for the timeseries model."
            in errors[0]["ctx"]["error"].args[0]
        )

    @pytest.mark.parametrize(
        "shape_type",
        [
            ShapeType.constant,
            ShapeType.gaussian,
            ShapeType.triangle,
        ],
    )
    def test_TimeseriesModel_invalid_input_simple_shapetypes_neither_peak_nor_cumulative(
        self, shape_type
    ):
        # Arrange
        model = self.get_test_model(shape_type)
        model.pop("peak_value")
        if "cumulative" in model:
            model.pop("cumulative")

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Either peak_value or cumulative must be specified for the timeseries model."
            in errors[0]["ctx"]["error"].args[0]
        )


class TestSyntheticTimeseries:
    @staticmethod
    def get_test_timeseries(scs=False):
        ts = SyntheticTimeseries()
        if scs:
            ts.attrs = SyntheticTimeseriesModel(
                shape_type=ShapeType.scs,
                peak_time=UnitfulTime(3, UnitTypesTime.hours),
                duration=UnitfulTime(6, UnitTypesTime.hours),
                cumulative=UnitfulLength(10, UnitTypesLength.inch),
                scs_file_name="scs_rainfall.csv",
                scs_type=Scstype.type3,
            )
        else:
            ts.attrs = SyntheticTimeseriesModel(
                shape_type=ShapeType.constant,
                peak_time=UnitfulTime(0, UnitTypesTime.hours),
                duration=UnitfulTime(1, UnitTypesTime.hours),
                peak_value=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
            )
        return ts

    def test_calculate_data_normal(self):
        ts = self.get_test_timeseries()

        timestep = UnitfulTime(1, UnitTypesTime.seconds)
        data = ts.calculate_data(timestep)

        assert (
            ts.attrs.duration / timestep == len(data) - 1
        ), f"{ts.attrs.duration}/{timestep} should eq {ts.attrs.duration/timestep}, but it is: {len(data) - 1}."
        assert np.amax(data) == ts.attrs.peak_value.value

    def test_calculate_data_scs(self):
        ts = self.get_test_timeseries(scs=True)
        timestep = UnitfulTime(1, UnitTypesTime.seconds)

        df = ts.to_dataframe(
            start_time=REFERENCE_TIME,
            end_time=REFERENCE_TIME + ts.attrs.duration.to_timedelta(),
            time_step=timestep,
        )

        dt = df.index.to_series().diff().dt.total_seconds().to_numpy()

        cum_rainfall_ts = np.sum(df.to_numpy().squeeze() * dt[1:].mean()) / 3600
        cum_rainfall_toml = ts.attrs.cumulative.value
        assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01
        assert isinstance(df, pd.DataFrame)
        assert (
            ts.attrs.duration / timestep == len(df.index) - 1
        ), f"{ts.attrs.duration}/{timestep} should eq {ts.attrs.duration/timestep}, but it is: {len(df.index) - 1}."

    def test_load_file(self):
        fd, path = tempfile.mkstemp(suffix=".toml")
        try:
            with os.fdopen(fd, "w") as tmp:
                # Write to the file
                tmp.write(
                    """
                shape_type = "constant"
                peak_time = { value = 0, units = "hours" }
                duration = { value = 1, units = "hours" }
                peak_value = { value = 1, units = "mm/hr" }
                """
                )

            try:
                model = SyntheticTimeseries.load_file(path)
            except Exception as e:
                pytest.fail(str(e))

            assert model.attrs.shape_type == ShapeType.constant
            assert model.attrs.peak_time == UnitfulTime(
                value=0, units=UnitTypesTime.hours
            )
            assert model.attrs.duration == UnitfulTime(
                value=1, units=UnitTypesTime.hours
            )
            assert model.attrs.peak_value == UnitfulIntensity(
                1, UnitTypesIntensity.mm_hr
            )

        finally:
            os.remove(path)

    def test_save(self):
        try:
            ts = SyntheticTimeseries()
            temp_path = "test.toml"
            ts.attrs = SyntheticTimeseriesModel(
                shape_type=ShapeType.constant,
                peak_time=UnitfulTime(value=0, units=UnitTypesTime.hours),
                duration=UnitfulTime(value=1, units=UnitTypesTime.hours),
                peak_value=UnitfulIntensity(value=1, units=UnitTypesIntensity.mm_hr),
            )
            try:
                ts.save(temp_path)
            except Exception as e:
                pytest.fail(str(e))

            assert os.path.exists(temp_path)

        finally:
            os.remove(temp_path)

    def test_to_dataframe(self):
        duration = UnitfulTime(2, UnitTypesTime.hours)
        ts = SyntheticTimeseries().load_dict(
            {
                "shape_type": "constant",
                "peak_time": {"value": 1, "units": "hours"},
                "duration": {"value": 2, "units": "hours"},
                "peak_value": {"value": 1, "units": UnitTypesIntensity.mm_hr},
            }
        )
        start = REFERENCE_TIME
        end = start + duration.to_timedelta()
        timestep = UnitfulTime(value=10, units=UnitTypesTime.seconds)

        # Call the to_dataframe method
        df = ts.to_dataframe(
            start_time=start,
            end_time=end,
            time_step=timestep,
        )

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["data_0"]
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_data = ts.calculate_data(
            time_step=UnitfulTime(value=timestep.value, units=UnitTypesTime.seconds)
        )
        expected_time_range = pd.date_range(
            start=REFERENCE_TIME,
            end=end,
            freq=timestep.to_timedelta(),
        )
        expected_df = pd.DataFrame(
            expected_data, columns=["data_0"], index=expected_time_range
        )
        expected_df.index.name = "time"
        pd.testing.assert_frame_equal(df, expected_df)
