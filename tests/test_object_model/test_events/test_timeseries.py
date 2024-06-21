import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from flood_adapt.object_model.hazard.event.timeseries import (
    Scstype,
    ShapeType,
    SyntheticTimeseries,
    SyntheticTimeseriesModel,
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
    def get_test_model(shape_type: ShapeType):
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
            "scs_file_path": "test_scs.csv",
            "scs_type": Scstype.type1.value,
        }

        models = {
            ShapeType.constant: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.gaussian: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.triangle: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.harmonic: _TIMESERIES_MODEL_SIMPLE,
            ShapeType.scs: _TIMESERIES_MODEL_SCS,
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
        assert timeseries_model.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert timeseries_model.end_time == UnitfulTime(1, UnitTypesTime.hours)
        assert timeseries_model.peak_intensity == UnitfulIntensity(
            1, UnitTypesIntensity.mm_hr
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

    def test_TimeseriesModel_valid_input_scs_shapetype(self, tmp_path):
        # Arrange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_test_model(ShapeType.scs)
        model["scs_file_path"] = Path(temp_file)

        # Act
        timeseries_model = SyntheticTimeseriesModel.model_validate(model)

        # Assert
        assert timeseries_model.shape_type == ShapeType.scs
        assert timeseries_model.start_time == UnitfulTime(0, UnitTypesTime.hours)
        assert timeseries_model.end_time == UnitfulTime(1, UnitTypesTime.hours)
        assert timeseries_model.cumulative == UnitfulLength(
            1, UnitTypesLength.millimeters
        )
        assert timeseries_model.scs_file_path == Path(temp_file)
        assert timeseries_model.scs_type == Scstype.type1

    @pytest.mark.parametrize("to_remove", ["scs_type", "scs_file_path", "cumulative"])
    def test_TimeseriesModel_invalid_input_shapetype_scs(self, tmp_path, to_remove):
        # Arrange
        temp_file = tmp_path / "data.csv"
        temp_file.write_text("test")
        model = self.get_test_model(ShapeType.scs)
        model["scs_file_path"] = Path(temp_file)
        model.pop(to_remove)

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "scs_file, scs_type and cumulative must be provided for SCS timeseries:"
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
        # Arrange
        model = self.get_test_model(shape_type)
        model["peak_intensity"] = {"value": 1, "units": UnitTypesIntensity.mm_hr}
        model["cumulative"] = {"value": 1, "units": UnitTypesLength.millimeters}

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

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
        # Arrange
        model = self.get_test_model(shape_type)
        model.pop("peak_intensity")
        if "cumulative" in model:
            model.pop("cumulative")

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

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
        # Arrange
        model = self.get_test_model(ShapeType.constant)
        model["start_time"]["value"] = 1
        model["end_time"]["value"] = 0

        # Act
        with pytest.raises(ValidationError) as e:
            SyntheticTimeseriesModel.model_validate(model)

        # Assert
        errors = e.value.errors()
        assert len(errors) == 1
        assert (
            "Timeseries start time cannot be later than its end time:"
            in errors[0]["ctx"]["error"].args[0]
        )


class TestSyntheticTimeseries:
    @staticmethod
    def get_test_timeseries():
        ts = SyntheticTimeseries()
        ts.attrs = SyntheticTimeseriesModel(
            shape_type=ShapeType.constant,
            start_time=UnitfulTime(0, UnitTypesTime.hours),
            end_time=UnitfulTime(1, UnitTypesTime.hours),
            peak_intensity=UnitfulIntensity(1, UnitTypesIntensity.mm_hr),
        )
        return ts

    def test_calculate_data(self):
        ts = self.get_test_timeseries()

        duration = (ts.attrs.end_time - ts.attrs.start_time).convert(
            UnitTypesTime.seconds
        )
        timestep = UnitfulTime(1, UnitTypesTime.seconds)
        data = ts.calculate_data(timestep)

        assert (duration.value / timestep.value) == len(data)
        assert np.amax(data) == ts.attrs.peak_intensity.value

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
                model = SyntheticTimeseries.load_file(path)
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
            ts = SyntheticTimeseries()
            temp_path = "test.toml"
            ts.attrs = SyntheticTimeseriesModel(
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

        ts = SyntheticTimeseries().load_dict(
            {
                "shape_type": "constant",
                "start_time": {"value": 0, "units": "hours"},
                "end_time": {"value": 2, "units": "hours"},
                "peak_intensity": {"value": 1, "units": "mm/hr"},
            }
        )
        start = "2020-01-02 00:00:00"
        end = "2020-01-02 02:00:00"

        # Call the to_dataframe method
        df = ts.to_dataframe(
            start_time=start,
            end_time=end,
            time_step=UnitfulTime(10, UnitTypesTime.seconds),
        )

        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ["intensity"]
        assert list(df.index.names) == ["time"]

        # Check that the DataFrame has the correct content
        expected_data = ts.calculate_data(
            time_step=UnitfulTime(10, UnitTypesTime.seconds)
        )
        expected_time_range = pd.date_range(
            start=pd.Timestamp(start), end=end, freq="10S", inclusive="left"
        )
        expected_df = pd.DataFrame(
            expected_data, columns=["intensity"], index=expected_time_range
        )
        expected_df.index.name = "time"

        pd.testing.assert_frame_equal(df, expected_df)
