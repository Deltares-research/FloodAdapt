from copy import deepcopy
from datetime import datetime

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.surge import SurgeSource
from flood_adapt.object_model.hazard.tide import TideSource
from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    EventModel,
    ShapeType,
    SurgeModel,
    TideModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulTime, UnitTypesTime
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
    def test_compute_rainfall_ts(
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
        ) + 1

        expected_columns = ["intensity"]
        expected_index = ["time"]

        event = Event.load_dict(event_model)

        # Act
        rainfall_df = event.compute_rainfall_ts(time_step=time_step)
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
            tend
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
        event = Event.load_dict(event_model)

        # Set up surge timeseries
        surge_timeseries = {
            "time": {
                "start_time": "2020-01-01 00:00:00",
                "end_time": "2020-01-02 00:00:00",
            },
            "values": [1, 2, 3, 4, 5],
        }
        surge_model = SurgeModel(
            source=SurgeSource.timeseries, timeseries=surge_timeseries
        )
        event.attrs.overland.surge = surge_model

        # Set up tide timeseries
        tide_timeseries = {
            "time": {
                "start_time": "2020-01-01 00:00:00",
                "end_time": "2020-01-02 00:00:00",
            },
            "values": [0.5, 1.0, 1.5, 2.0, 2.5],
        }
        tide_model = TideModel(source=TideSource.timeseries, timeseries=tide_timeseries)
        event.attrs.overland.tide = tide_model

        expected_combined_ts = pd.DataFrame(
            {
                "time": pd.date_range(
                    start="2020-01-01 00:00:00", end="2020-01-02 00:00:00", freq="H"
                ),
                "value": [1.5, 3.0, 4.5, 6.0, 7.5],
            }
        )

        # Act
        event.add_tide_and_surge_ts()

        # Assert
        assert isinstance(event.tide_surge_ts, pd.DataFrame)
        assert event.tide_surge_ts.equals(expected_combined_ts)
