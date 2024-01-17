import glob
import os
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import tomli

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.interface.events import (
    Mode,
    RainfallModel,
    RiverModel,
    Template,
    TideModel,
    TimeModel,
    Timing,
    WindModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulVelocity,
)
from flood_adapt.object_model.site import (
    Site,
)

# @pytest.fixture
# def input_toml(test_db):
#     test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
#     yield test_toml

def test_get_template(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    # use event template to get the associated Event child class
    template = Event.get_template(test_toml)

    assert template == "Synthetic"

def test_get_mode(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    mode = Event.get_mode(test_toml)

    assert mode == "single_event"

def test_timeseries_shape_gaussian():
    cumulative=5.
    shape_duration=1.
    duration = 48 * 3600
    shape_duration = 3600
    peak = 8124.3 * cumulative / shape_duration
    time_shift = 24 * 3600
    shape = Event.timeseries_shape(
        shape_type="gaussian",
        duration=duration,
        peak=peak,
        shape_duration=shape_duration,
        time_shift=time_shift,
    )
    dt = 600
    cum_rainfall_ts = np.sum(shape * dt) / 3600
    assert np.abs(cum_rainfall_ts - cumulative) < 0.01

def test_timeseries_shape_block():
    duration = 48 * 3600
    peak = 5.
    shape = Event.timeseries_shape(
        shape_type="block",
        duration=duration,
        peak=peak,
        start_shape=0,
        end_shape=4*3600,
    )
    dt = 600
    cum_rainfall_ts = np.sum(shape * dt) / 3600
    cumulative = 4 * peak
    assert np.abs(cum_rainfall_ts - cumulative) < 0.01

def test_timeseries_shape_triangle():
    duration = 48 * 3600
    peak = 5.
    shape = Event.timeseries_shape(
        shape_type="triangle",
        duration=duration,
        peak=peak,
        start_shape=0,
        time_shift=3600,
        end_shape=4*3600,
    )
    dt = 600
    cum_rainfall_ts = np.sum(shape * dt) / 3600
    cumulative = 0.5 * 4 * peak
    assert np.abs(cum_rainfall_ts - cumulative) < 0.01

def test_read_csv(test_db):
    tt = pd.date_range(
        start="20200101 000000",
        end="20200301 000000",
        freq="1H",
    )
    rain = 100 * np.exp(-(((np.arange(0, len(tt), 1) - 24) / (0.25 * 12)) ** 2)).round(
        decimals=2
    )
    df = pd.DataFrame(index=tt, data=rain)
    fn = test_db.input_path.joinpath("events","rainfall.csv")
    df.to_csv(fn, header=None)

    df_out = Event.read_csv(fn)

    assert isinstance(df_out, pd.DataFrame)
    assert isinstance(df_out.index, pd.DatetimeIndex)