from copy import deepcopy
from datetime import datetime

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    EventModel,
    ShapeType,
    SurgeModel,
    SurgeSource,
    TideModel,
    TideSource,
)
from flood_adapt.object_model.io.timeseries import Timeseries
from flood_adapt.object_model.io.unitfulvalue import UnitfulTime, UnitTypesTime
from tests.test_io.test_timeseries import TestTimeseriesModel
from tests.test_object_model.test_event_models import TestEventModel

plot = False  # True


class TestEvent:
    @staticmethod
    def get_test_event():
        event_model = TestEventModel.get_test_model()
        event = Event.load_dict(event_model)
        return deepcopy(event)

    @staticmethod
    def get_test_event_model():
        event_model = EventModel.model_validate(TestEventModel.get_test_model())
        return deepcopy(event_model)

    @pytest.mark.parametrize(
        "ts_start, ts_end, event_start, event_end, timestep, shape_type",
        [
            (1, 2, "2020-01-01 00:00:00", "2020-01-02 00:10:00", 1, ShapeType.gaussian),
            (1, 2, "2020-01-01 00:10:00", "2020-01-02 20:00:00", 1, ShapeType.constant),
            (
                10,
                50,
                "2020-01-01 00:00:00",
                "2020-01-05 00:00:00",
                600,
                ShapeType.harmonic,
            ),
            (1, 2, "2020-01-01 15:00:00", "2020-01-04 01:10:00", 1, ShapeType.triangle),
        ],
    )
    def test_add_rainfall_ts(
        self, ts_start, ts_end, event_start, event_end, timestep, shape_type
    ):
        # Arange
        event_model = EventModel.model_validate(TestEventModel.get_test_model())
        event_model.time.start_time = event_start
        event_model.time.end_time = event_end

        event_model.overland.rainfall.timeseries.start_time = UnitfulTime(
            ts_start, UnitTypesTime.hours
        )
        event_model.overland.rainfall.timeseries.end_time = UnitfulTime(
            ts_end, UnitTypesTime.hours
        )
        event_model.overland.rainfall.timeseries.shape_type = shape_type
        event_model = EventModel.model_validate(event_model)

        tstart = datetime.strptime(event_model.time.start_time, DEFAULT_DATETIME_FORMAT)
        tend = datetime.strptime(event_model.time.end_time, DEFAULT_DATETIME_FORMAT)
        time_step = UnitfulTime(timestep, UnitTypesTime.seconds)

        expected_length = (tend - tstart).total_seconds() / int(
            time_step.convert(UnitTypesTime.seconds).value
        )

        expected_columns = ["intensity"]
        expected_index = ["time"]

        event = Event.load_dict(event_model)

        # Act
        event.add_rainfall_ts(time_step=time_step)
        rainfall_df = event.rainfall_ts

        if plot:
            import matplotlib.pyplot as plt

            rainfall_df.plot()
            plt.show()

        # Assert
        assert isinstance(
            rainfall_df, pd.DataFrame
        ), f"Expected rainfall_df to be a DataFrame, but got {type(rainfall_df)}"

        assert rainfall_df.index[0] == pd.Timestamp(
            tstart
        ), f"Expected first index of rainfall_df to be {pd.Timestamp(tstart)}, but got {rainfall_df.index[0]}"

        assert rainfall_df.index[-1] == pd.Timestamp(
            tend - pd.Timedelta(seconds=time_step.convert(UnitTypesTime.seconds).value)
        ), f"Expected last index of rainfall_df to be {pd.Timestamp(tend)}, but got {rainfall_df.index[-1]}"

        assert (
            len(rainfall_df) == expected_length
        ), f"Expected length of rainfall_df to be {expected_length}, but got {len(rainfall_df)}"

        assert (
            rainfall_df.columns.tolist() == expected_columns
        ), f"Expected columns of rainfall_df to be {expected_columns}, but got {rainfall_df.columns.tolist()}"

        assert (
            rainfall_df.index.names == expected_index
        ), f"Expected index names of rainfall_df to be {expected_index}, but got {rainfall_df.index.names}"

    def test_add_tide_and_surge_ts(self):
        # Arrange
        event_model = TestEventModel.get_test_model()
        start = "2020-01-01 00:00:00"
        end = "2020-01-01 01:00:00"
        timestep = UnitfulTime(1, UnitTypesTime.minutes)
        event_model["time"]["start_time"] = start
        event_model["time"]["end_time"] = end
        event = Event.load_dict(event_model)

        # Set up surge timeseries
        surge_ts_model = TestTimeseriesModel.get_test_model(
            shape_type=ShapeType.gaussian
        )
        event.attrs.overland.surge = SurgeModel(
            source=SurgeSource.timeseries, timeseries=surge_ts_model
        )

        # Set up tide timeseries
        tide_ts_model = TestTimeseriesModel.get_test_model(
            shape_type=ShapeType.harmonic
        )
        event.attrs.overland.tide = TideModel(
            source=TideSource.timeseries, timeseries=tide_ts_model
        )

        # Manually add tide and surge timeseries
        surge_ts = Timeseries.load_dict(surge_ts_model).to_dataframe(
            start_time=start,
            end_time=end,
            time_step=timestep,
        )
        tide_ts = Timeseries.load_dict(tide_ts_model).to_dataframe(
            start_time=start,
            end_time=end,
            time_step=timestep,
        )
        expected_combined_ts = surge_ts.add(tide_ts, axis="index", fill_value=0)

        # Update event
        event = Event.load_dict(event.attrs)

        # Act
        event = event.add_tide_and_surge_ts(time_step=timestep)
        print(event.tide_surge_ts)
        print(expected_combined_ts)

        # Assert
        assert isinstance(event.tide_surge_ts, pd.DataFrame)
        pd.testing.assert_frame_equal(event.tide_surge_ts, expected_combined_ts)
