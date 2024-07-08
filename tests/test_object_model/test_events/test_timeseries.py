import os
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from flood_adapt.object_model.hazard.event.timeseries import (
    # Scstype,
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
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
        # _TIMESERIES_MODEL_SCS = {
        #     "shape_type": ShapeType.scs.value,
        #     "peak_time": {"value": 0, "units": UnitTypesTime.hours},
        #     "duration": {"value": 1, "units": UnitTypesTime.hours},
        #     "cumulative": {"value": 1, "units": UnitTypesLength.millimeters},
        #     "scs_file_path": "test_scs.csv",
        #     "scs_type": Scstype.type1.value,
        # }

        models = {
            ShapeType.constant: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.gaussian: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.triangle: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.harmonic: _TIMESERIES_MODEL_SIMPLE,
            # ShapeType.scs: _TIMESERIES_MODEL_SCS,
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

    # def test_TimeseriesModel_valid_input_scs_shapetype(self, tmp_path):
    #     # Arrange
    #     temp_file = tmp_path / "data.csv"
    #     temp_file.write_text("test")
    #     model = self.get_test_model(ShapeType.scs)
    #     model["scs_file_path"] = Path(temp_file)

    #     # Act
    #     timeseries_model = SyntheticTimeseriesModel.model_validate(model)

    #     # Assert
    #     assert timeseries_model.shape_type == ShapeType.scs
    #     assert timeseries_model.peak_time == UnitfulTime(0, UnitTypesTime.hours)
    #     assert timeseries_model.duration == UnitfulTime(1, UnitTypesTime.hours)
    #     assert timeseries_model.cumulative == UnitfulLength(
    #         1, UnitTypesLength.millimeters
    #     )
    # assert timeseries_model.scs_file_path == Path(temp_file)
    # assert timeseries_model.scs_type == Scstype.type1

    # @pytest.mark.parametrize("to_remove", ["scs_type", "scs_file_path", "cumulative"])
    # def test_TimeseriesModel_invalid_input_shapetype_scs(self, tmp_path, to_remove):
    #     # Arrange
    #     temp_file = tmp_path / "data.csv"
    #     temp_file.write_text("test")
    #     model = self.get_test_model(ShapeType.scs)
    #     model["scs_file_path"] = Path(temp_file)
    #     model.pop(to_remove)

    #     # Act
    #     with pytest.raises(ValidationError) as e:
    #         SyntheticTimeseriesModel.model_validate(model)

    #     # Assert
    #     errors = e.value.errors()
    #     assert len(errors) == 1
    #     assert (
    #         "scs_file, scs_type and cumulative must be provided for SCS timeseries:"
    #         in errors[0]["ctx"]["error"].args[0]
    #     )

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
            ShapeType.harmonic,
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
    def get_test_timeseries():
        ts = SyntheticTimeseries()
        ts.attrs = SyntheticTimeseriesModel(
            shape_type=ShapeType.constant,
            peak_time=UnitfulTime(0, UnitTypesTime.hours),
            duration=UnitfulTime(1, UnitTypesTime.hours),
            peak_value=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
        )
        return ts

    def test_calculate_data(self):
        ts = self.get_test_timeseries()

        timestep = UnitfulTime(1, UnitTypesTime.seconds)
        data = ts.calculate_data(timestep)

        assert int(ts.attrs.duration / timestep) == len(
            data
        ), f"{ts.attrs.duration}/{timestep} should eq {len(data)}, but it is: {ts.attrs.duration/timestep}."
        assert np.amax(data) == ts.attrs.peak_value.value

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
                peak_value = { value = 1, units = "mm_hr" }
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
        start = datetime(year=2020, month=1, day=1, hour=2)
        end = start + duration.to_timedelta()
        timestep = UnitfulTime(value=10, units=UnitTypesTime.seconds)

        # Call the to_dataframe method
        df = ts.to_dataframe(
            start_time=start,
            end_time=end,
            time_step=timestep,
        )

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["values"]
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_data = ts.calculate_data(
            time_step=UnitfulTime(value=timestep.value, units=UnitTypesTime.seconds)
        )
        expected_time_range = pd.date_range(
            start=pd.Timestamp(start),
            end=end,
            freq=f"{int(timestep.value)}S",
            inclusive="left",
        )
        expected_df = pd.DataFrame(
            expected_data, columns=["values"], index=expected_time_range
        )
        expected_df.index.name = "time"
        pd.testing.assert_frame_equal(df, expected_df)
