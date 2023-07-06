from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import tomli

from flood_adapt.dbs_controller import Database
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

test_database = Path().absolute() / "tests" / "test_database"


def test_get_template():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )

    assert test_toml.is_file()

    with open(str(test_toml), mode="rb") as fp:
        tomli.load(fp)

    # use event template to get the associated Event child class
    template = Event.get_template(test_toml)

    assert template == "Synthetic"


def test_load_and_save_fromtoml_synthetic():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )

    test_save_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft_test.toml"
    )

    assert test_toml.is_file()

    with open(str(test_toml), mode="rb") as fp:
        tomli.load(fp)

    # use event template to get the associated Event child class
    template = Event.get_template(test_toml)
    test_synthetic = EventFactory.get_event(template).load_file(test_toml)

    # assert that attributes have been set to correct data types
    assert test_synthetic
    assert isinstance(test_synthetic.attrs.name, str)
    assert isinstance(test_synthetic.attrs.long_name, str)
    assert isinstance(test_synthetic.attrs.mode, Mode)
    assert isinstance(test_synthetic.attrs.template, Template)
    assert isinstance(test_synthetic.attrs.timing, Timing)
    assert isinstance(test_synthetic.attrs.water_level_offset, UnitfulLength)
    assert isinstance(test_synthetic.attrs.time, TimeModel)
    assert isinstance(test_synthetic.attrs.tide, TideModel)
    # assert isinstance(test_synthetic.attrs.surge, dict)
    # assert isinstance(test_synthetic.attrs.wind, dict)
    # assert isinstance(test_synthetic.attrs.rainfall, dict)
    # assert isinstance(test_synthetic.attrs.river, dict)

    # assert that attributes have been set to values from toml file
    assert test_synthetic.attrs
    assert test_synthetic.attrs.name == "extreme12ft"
    assert test_synthetic.attrs.long_name == "extreme 12 foot event"
    assert test_synthetic.attrs.template == "Synthetic"
    assert test_synthetic.attrs.timing == "idealized"
    assert test_synthetic.attrs.water_level_offset.value == 0
    assert test_synthetic.attrs.water_level_offset.units == "feet"
    assert test_synthetic.attrs.time.duration_before_t0 == 24.0
    assert test_synthetic.attrs.time.duration_after_t0 == 24.0
    assert test_synthetic.attrs.tide.source == "harmonic"
    assert test_synthetic.attrs.tide.harmonic_amplitude.value == 3
    assert test_synthetic.attrs.tide.harmonic_amplitude.units == "feet"
    # assert test_synthetic.attrs.surge["source"] == "shape"
    # assert test_synthetic.attrs.surge["shape_type"] == "gaussian"
    # assert test_synthetic.attrs.surge["shape_peak"]["value"] == 9.22
    # assert test_synthetic.attrs.surge["shape_peak"]["units"] == "feet"
    # assert test_synthetic.attrs.surge["shape_duration"] == 24
    # assert test_synthetic.attrs.surge["shape_peak_time"] == 0
    # assert test_synthetic.attrs.surge["panel_text"] == "Storm Surge"
    # assert test_synthetic.attrs.wind["source"] == "constant"
    # assert test_synthetic.attrs.wind["constant_speed"]["value"] == 0
    # assert test_synthetic.attrs.wind["constant_speed"]["units"] == "m/s"
    # assert test_synthetic.attrs.wind["constant_direction"]["value"] == 0
    # assert test_synthetic.attrs.wind["constant_direction"]["units"] == "deg N"
    # assert test_synthetic.attrs.rainfall["source"] == "none"
    # assert test_synthetic.attrs.river["source"] == "constant"
    # assert test_synthetic.attrs.river["constant_discharge"]["value"] == 5000
    # assert test_synthetic.attrs.river["constant_discharge"]["units"] == "cfs"

    # ensure it's saving a file
    test_synthetic.save(test_save_toml)
    test_save_toml.unlink()  # added this to delete the file afterwards


def test_download_meteo():
    event_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "kingTideNov2021"
        / "kingTideNov2021.toml"
    )
    kingTide = HistoricalOffshore.load_file(event_toml)

    site_toml = test_database / "charleston" / "static" / "site" / "site.toml"

    site = Site.load_file(site_toml)
    path = test_database / "charleston" / "input" / "events" / "kingTideNov2021"
    gfs_conus = kingTide.download_meteo(site=site, path=path)

    assert gfs_conus


def test_download_wl_timeseries():
    station_id = 8665530
    start_time_str = "20230101 000000"
    stop_time_str = "20230102 000000"

    wl_df = HistoricalNearshore.download_wl_data(
        station_id, start_time_str, stop_time_str
    )

    assert wl_df.index[0] == datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
    assert wl_df.iloc[:, 0].dtypes == "float64"


def test_constant_rainfall():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.rainfall = RainfallModel(
        source="constant",
        constant_intensity=UnitfulIntensity(value=2.0, units="inch/hr"),
    )
    event.add_rainfall_ts()
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    assert np.abs(event.rain_ts.to_numpy()[0][0] - 2) < 0.001


def test_gaussian_rainfall():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.rainfall = RainfallModel(
        source="shape",
        cumulative=UnitfulLength(value=5.0, units="inch"),
        shape_type="gaussian",
        shape_duration=1,
        shape_peak_time=0,
    )
    event.add_rainfall_ts()
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    # event.rain_ts.to_csv(
    #     (test_database / "charleston" / "input" / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.convert("millimeters")
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_block_rainfall():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.rainfall = RainfallModel(
        source="shape",
        cumulative=UnitfulLength(value=10.0, units="inch"),
        shape_type="block",
        shape_start_time=-24,
        shape_end_time=-20,
    )
    event.add_rainfall_ts()
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    # event.rain_ts.to_csv(
    #     (test_database / "charleston" / "input" / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.convert("millimeters")
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_triangle_rainfall():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.rainfall = RainfallModel(
        source="shape",
        cumulative=UnitfulLength(value=10.0, units="inch"),
        shape_type="triangle",
        shape_start_time=-24,
        shape_end_time=-20,
        shape_peak_time=-23,
    )
    event.add_rainfall_ts()
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    # event.rain_ts.to_csv(
    #     (test_database / "charleston" / "input" / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.convert("millimeters")
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_constant_wind():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.wind = WindModel(
        source="constant",
        constant_speed=UnitfulVelocity(value=20.0, units="m/s"),
        constant_direction=UnitfulDirection(value=90, units="deg N"),
    )
    event.add_wind_ts()
    assert isinstance(event.wind_ts, pd.DataFrame)
    assert isinstance(event.wind_ts.index, pd.DatetimeIndex)
    assert np.abs(event.wind_ts.to_numpy()[0][0] - 20) < 0.001


def test_constant_discharge():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = RiverModel(
        source="constant",
        constant_discharge=UnitfulDischarge(value=2000.0, units="cfs"),
    )
    event.add_dis_ts()
    assert isinstance(event.dis_ts, pd.DataFrame)
    assert isinstance(event.dis_ts.index, pd.DatetimeIndex)
    const_dis = event.attrs.river.constant_discharge.convert("m3/s")

    assert np.abs(event.dis_ts.to_numpy()[0][0] - (const_dis)) < 0.001


def test_gaussian_discharge():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = RiverModel(
        source="shape",
        shape_type="gaussian",
        shape_duration=2.0,
        shape_peak_time=-22.0,
        base_discharge=UnitfulDischarge(value=5000, units="cfs"),
        shape_peak=UnitfulDischarge(value=10000, units="cfs"),
    )
    event.add_dis_ts()
    assert isinstance(event.dis_ts, pd.DataFrame)
    assert isinstance(event.dis_ts.index, pd.DatetimeIndex)
    # event.dis_ts.to_csv(
    #     (
    #         test_database
    #         / "charleston"
    #         / "input"
    #         / "events"
    #         / "extreme12ft"
    #         / "river.csv"
    #     )
    # )
    dt = event.dis_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_dis_ts = np.sum(event.dis_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    assert np.abs(cum_dis_ts - 6945.8866666) < 0.01


def test_block_discharge():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "events"
        / "extreme12ft"
        / "extreme12ft.toml"
    )
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = RiverModel(
        source="shape",
        base_discharge=UnitfulDischarge(value=5000, units="cfs"),
        shape_peak=UnitfulDischarge(value=10000, units="cfs"),
        shape_type="block",
        shape_start_time=-24.0,
        shape_end_time=-20.0,
    )
    event.add_dis_ts()
    assert isinstance(event.dis_ts, pd.DataFrame)
    assert isinstance(event.dis_ts.index, pd.DatetimeIndex)
    # event.dis_ts.to_csv(
    #     (
    #         test_database
    #         / "charleston"
    #         / "input"
    #         / "events"
    #         / "extreme12ft"
    #         / "river.csv"
    #     )
    # )
    dt = event.dis_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_dis_ts = np.sum(event.dis_ts.to_numpy().squeeze() * dt[1:].mean())
    assert (
        np.abs(event.dis_ts[1][0] - event.attrs.river.shape_peak.convert("m3/s"))
        < 0.001
    )
    assert (
        np.abs(event.dis_ts[1][-1] - event.attrs.river.base_discharge.convert("m3/s"))
        < 0.001
    )
