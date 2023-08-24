import glob
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
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
    Template,
    TideModel,
    TimeModel,
    Timing,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity, UnitfulLength
from flood_adapt.object_model.site import (
    Site,
)

test_database = Path().absolute() / "tests" / "test_database"


def test_get_template(cleanup_database):
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


def test_load_and_save_fromtoml_synthetic(cleanup_database):
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

    # ensure it's saving a file
    test_synthetic.save(test_save_toml)
    test_save_toml.unlink()  # added this to delete the file afterwards


def test_load_from_toml_hurricane():
    test_toml = test_database / "charleston" / "input" / "events" / "ETA" / "ETA.toml"

    assert test_toml.is_file()

    with open(str(test_toml), mode="rb") as fp:
        tomli.load(fp)

    # use event template to get the associated Event child class
    print(test_toml)
    template = Event.get_template(test_toml)
    print(template)
    test_synthetic = EventFactory.get_event(template).load_file(test_toml)

    # assert that attributes have been set to correct data types
    assert test_synthetic
    assert isinstance(test_synthetic.attrs.name, str)
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
    assert test_synthetic.attrs.name == "ETA"
    assert test_synthetic.attrs.template == "Historical_hurricane"
    assert test_synthetic.attrs.timing == "historical"
    assert test_synthetic.attrs.water_level_offset.value == 0.6
    assert test_synthetic.attrs.water_level_offset.units == "feet"
    assert test_synthetic.attrs.tide.source == "model"
    assert test_synthetic.attrs.river.source == "constant"

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


def test_save_to_toml_hurricane():
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

    # ensure it's saving a file
    test_synthetic.save(test_save_toml)
    test_save_toml.unlink()  # added this to delete the file afterwards


def test_download_meteo(cleanup_database):
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

    # Delete files
    file_pattern = os.path.join(path, "*.nc")
    file_list = glob.glob(file_pattern)

    for file_path in file_list:
        os.remove(file_path)


def test_download_wl_timeseries(cleanup_database):
    station_id = 8665530
    start_time_str = "20230101 000000"
    stop_time_str = "20230102 000000"

    wl_df = HistoricalNearshore.download_wl_data(
        station_id, start_time_str, stop_time_str
    )

    assert wl_df.index[0] == datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
    assert wl_df.iloc[:, 0].dtypes == "float64"


def test_make_spw_file():
    event_toml = (
        test_database / "charleston" / "input" / "events" / "FLORENCE" / "FLORENCE.toml"
    )

    template = Event.get_template(event_toml)
    FLORENCE = EventFactory.get_event(template).load_file(event_toml)

    site_toml = test_database / "charleston" / "static" / "site" / "site.toml"
    site = Site.load_file(site_toml)

    FLORENCE.make_spw_file(
        database_path=test_database.joinpath("charleston"),
        model_dir=event_toml.parent,
        site=site,
    )

    assert event_toml.parent.joinpath("hurricane.spw").is_file()

    # Remove spw file after completion of test
    if event_toml.parent.joinpath("hurricane.spw").is_file():
        os.remove(event_toml.parent.joinpath("hurricane.spw"))


def test_translate_hurricane_track(cleanup_database):
    from cht_cyclones.tropical_cyclone import TropicalCyclone

    event_toml = (
        test_database / "charleston" / "input" / "events" / "FLORENCE" / "FLORENCE.toml"
    )

    template = Event.get_template(event_toml)
    FLORENCE = EventFactory.get_event(template).load_file(event_toml)

    site_toml = test_database / "charleston" / "static" / "site" / "site.toml"
    site = Site.load_file(site_toml)

    tc = TropicalCyclone()
    tc.read_track(filename=event_toml.parent.joinpath("FLORENCE.cyc"), fmt="ddb_cyc")
    ref = tc.track

    # Add translation to FLORENCE
    dx = 10000
    dy = 25000
    FLORENCE.attrs.hurricane_translation.eastwest_translation.value = dx
    FLORENCE.attrs.hurricane_translation.eastwest_translation.units = "meters"
    FLORENCE.attrs.hurricane_translation.northsouth_translation.value = dy
    FLORENCE.attrs.hurricane_translation.northsouth_translation.units = "meters"

    tc = FLORENCE.translate_tc_track(tc=tc, site=site)
    new = tc.track

    # Determine difference in coordinates between the tracks
    geom_new = new.iloc[0, 1]
    geom_ref = ref.iloc[0, 1]
    # Subtract the coordinates of the two geometries
    diff_lat = geom_new.coords[0][0] - geom_ref.coords[0][0]
    diff_lon = geom_new.coords[0][1] - geom_ref.coords[0][1]
    assert round(diff_lat, 2) == 0.09
    assert round(diff_lon, 2) == 0.08


def test_constant_rainfall(cleanup_database):
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


def test_gaussian_rainfall(cleanup_database):
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


def test_block_rainfall(cleanup_database):
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


def test_triangle_rainfall(cleanup_database):
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


def test_scs_rainfall(cleanup_database):
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
        shape_type="scs",
        shape_start_time=-24,
        shape_duration=6,
    )
    scsfile = test_database / "charleston" / "static" / "scs" / "scs_rainfall.csv"
    event.add_rainfall_ts(scsfile=scsfile, scstype="type_3")
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    # event.rain_ts.to_csv(
    #     (test_database / "charleston" / "input" / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.convert("millimeters")
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01
