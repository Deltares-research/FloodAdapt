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


def test_get_template(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"

    assert test_toml.is_file()

    with open(str(test_toml), mode="rb") as fp:
        tomli.load(fp)

    # use event template to get the associated Event child class
    template = Event.get_template(test_toml)

    assert template == "Synthetic"


def test_load_and_save_fromtoml_synthetic(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"

    test_save_toml = (
        test_db.input_path / "events" / "extreme12ft" / "extreme12ft_test.toml"
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


def test_load_from_toml_hurricane(test_db):
    test_toml = test_db.input_path / "events" / "ETA" / "ETA.toml"

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
    assert test_synthetic.attrs.river[0].source == "constant"

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


def test_save_to_toml_hurricane(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"

    test_save_toml = (
        test_db.input_path / "events" / "extreme12ft" / "extreme12ft_test.toml"
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


@pytest.mark.skip(reason="This right now takes ages to run! Check why!")
def test_download_meteo(test_db):
    event_toml = (
        test_db.input_path / "events" / "kingTideNov2021" / "kingTideNov2021.toml"
    )

    kingTide = HistoricalOffshore.load_file(event_toml)

    site_toml = test_db.static_path / "site" / "site.toml"

    site = Site.load_file(site_toml)
    path = test_db.input_path / "events" / "kingTideNov2021"
    gfs_conus = kingTide.download_meteo(site=site, path=path)

    assert gfs_conus

    # Delete files
    file_pattern = os.path.join(path, "*.nc")
    file_list = glob.glob(file_pattern)

    for file_path in file_list:
        os.remove(file_path)

    # Delete files
    file_pattern = os.path.join(path, "*.nc")
    file_list = glob.glob(file_pattern)

    for file_path in file_list:
        os.remove(file_path)


def test_download_wl_timeseries(test_db):
    station_id = 8665530
    start_time_str = "20230101 000000"
    stop_time_str = "20230102 000000"
    site_toml = test_db.static_path / "site" / "site.toml"
    site = Site.load_file(site_toml)
    wl_df = HistoricalNearshore.download_wl_data(
        station_id,
        start_time_str,
        stop_time_str,
        units="feet",
        source=site.attrs.tide_gauge.source,
        file=None,
    )

    assert wl_df.index[0] == datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
    assert wl_df.iloc[:, 0].dtypes == "float64"


def test_make_spw_file(test_db):
    event_toml = test_db.input_path / "events" / "FLORENCE" / "FLORENCE.toml"

    template = Event.get_template(event_toml)
    FLORENCE = EventFactory.get_event(template).load_file(event_toml)

    site_toml = test_db.static_path / "site" / "site.toml"
    site = Site.load_file(site_toml)

    FLORENCE.make_spw_file(
        event_path=event_toml.parent,
        model_dir=event_toml.parent,
        site=site,
    )

    assert event_toml.parent.joinpath("hurricane.spw").is_file()

    # Remove spw file after completion of test
    if event_toml.parent.joinpath("hurricane.spw").is_file():
        os.remove(event_toml.parent.joinpath("hurricane.spw"))


def test_translate_hurricane_track(test_db):
    from cht_cyclones.tropical_cyclone import TropicalCyclone

    event_toml = test_db.input_path / "events" / "FLORENCE" / "FLORENCE.toml"

    template = Event.get_template(event_toml)
    FLORENCE = EventFactory.get_event(template).load_file(event_toml)

    site_toml = test_db.static_path / "site" / "site.toml"
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


def test_constant_rainfall(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.rainfall = RainfallModel(
        source="constant",
        constant_intensity=UnitfulIntensity(value=2.0, units="inch/hr"),
    )
    event.add_rainfall_ts()  # also converts to mm/hour!!!
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    assert (
        np.abs(
            event.rain_ts.to_numpy()[0][0]
            - UnitfulIntensity(value=2, units="inch/hr").value
        )
        < 0.001
    )


def test_gaussian_rainfall(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
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
    #     (test_db.input_path / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.value
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_block_rainfall(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
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
    #     (test_db.input_path / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.value
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_triangle_rainfall(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
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
    #     (test_db.input_path / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.value
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_scs_rainfall(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
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
    scsfile = test_db.static_path / "scs" / "scs_rainfall.csv"
    event.add_rainfall_ts(scsfile=scsfile, scstype="type_3")
    assert isinstance(event.rain_ts, pd.DataFrame)
    assert isinstance(event.rain_ts.index, pd.DatetimeIndex)
    # event.rain_ts.to_csv(
    #     (test_db.input_path / "events" / "extreme12ft" / "rain.csv")
    # )
    dt = event.rain_ts.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_rainfall_ts = np.sum(event.rain_ts.to_numpy().squeeze() * dt[1:].mean()) / 3600
    cum_rainfall_toml = event.attrs.rainfall.cumulative.value
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


def test_constant_wind(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
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


def test_constant_discharge(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = [
        RiverModel(
            source="constant",
            constant_discharge=UnitfulDischarge(value=2000.0, units="cfs"),
        )
    ]
    site_toml = test_db.static_path / "site" / "site.toml"
    site = Site.load_file(site_toml)
    event.add_dis_ts(event_dir=test_toml.parent, site_river=site.attrs.river)
    assert isinstance(event.dis_df, pd.DataFrame)
    assert isinstance(event.dis_df.index, pd.DatetimeIndex)
    const_dis = event.attrs.river[0].constant_discharge.value

    assert np.abs(event.dis_df.to_numpy()[0][0] - (const_dis)) < 0.001


def test_gaussian_discharge(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = [
        RiverModel(
            source="shape",
            shape_type="gaussian",
            shape_duration=2.0,
            shape_peak_time=-22.0,
            base_discharge=UnitfulDischarge(value=5000, units="cfs"),
            shape_peak=UnitfulDischarge(value=10000, units="cfs"),
        )
    ]
    site_toml = test_db.static_path / "site" / "site.toml"
    site = Site.load_file(site_toml)
    event.add_dis_ts(event_dir=test_toml.parent, site_river=site.attrs.river)
    assert isinstance(event.dis_df, pd.DataFrame)
    assert isinstance(event.dis_df.index, pd.DatetimeIndex)
    # event.dis_df.to_csv(
    #     (
    #         test_database
    #         / "charleston"
    #         / "input"
    #         / "events"
    #         / "extreme12ft"
    #         / "river.csv"
    #     )
    # )
    dt = event.dis_df.index.to_series().diff().dt.total_seconds().to_numpy()
    cum_dis = np.sum(event.dis_df.to_numpy().squeeze() * dt[1:].mean()) / 3600
    assert (
        np.abs(
            UnitfulDischarge(value=cum_dis, units="cfs").convert("m3/s") - 6945.8866666
        )
        < 0.01
    )


def test_block_discharge(test_db):
    test_toml = test_db.input_path / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()
    template = Event.get_template(test_toml)
    # use event template to get the associated event child class
    event = EventFactory.get_event(template).load_file(test_toml)
    event.attrs.river = [
        RiverModel(
            source="shape",
            base_discharge=UnitfulDischarge(value=5000, units="cfs"),
            shape_peak=UnitfulDischarge(value=10000, units="cfs"),
            shape_type="block",
            shape_start_time=-24.0,
            shape_end_time=-20.0,
        )
    ]
    site_toml = test_db.static_path / "site" / "site.toml"
    site = Site.load_file(site_toml)
    event.add_dis_ts(event_dir=test_toml.parent, site_river=site.attrs.river)
    assert isinstance(event.dis_df, pd.DataFrame)
    assert isinstance(event.dis_df.index, pd.DatetimeIndex)
    # event.dis_df.to_csv(
    #     (
    #         test_database
    #         / "charleston"
    #         / "input"
    #         / "events"
    #         / "extreme12ft"
    #         / "river.csv"
    #     )
    # )
    assert np.abs(event.dis_df[1][0] - event.attrs.river[0].shape_peak.value) < 0.001
    assert (
        np.abs(event.dis_df[1][-1] - event.attrs.river[0].base_discharge.value) < 0.001
    )


class Test_ReadCSV:
    def write_dummy_csv(
        self, path, headers: bool, datetime_format: str, num_columns: int = 1
    ) -> pd.DataFrame:
        size = 20
        gen = np.random.default_rng()
        time = pd.date_range(start="2021-01-01", periods=size, freq="H")
        data = {f"data_{i}": gen.random(size) for i in range(num_columns)}

        df = pd.DataFrame(
            {
                "time": time,
                **data,
            }
        )
        df.to_csv(path, index=False, header=headers, date_format=datetime_format)

        df = df.set_index("time")
        df.columns = [i + 1 for i in range(num_columns)]
        return df

    def test_read_file_with_headers(self, tmp_path):
        # Arrange
        path = tmp_path / "withheaders.csv"
        test_df = self.write_dummy_csv(
            path, headers=True, datetime_format="%Y-%m-%d %H:%M:%S"
        )

        # Act
        df = Event.read_csv(path)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)

        pd.testing.assert_frame_equal(df, test_df, check_names=False)

    def test_read_file_without_headers(self, tmp_path):
        # Arrange
        path = tmp_path / "withoutheaders.csv"
        test_df = self.write_dummy_csv(
            path, headers=False, datetime_format="%Y-%m-%d %H:%M:%S"
        )

        # Act
        df = Event.read_csv(path)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)

        pd.testing.assert_frame_equal(df, test_df)

    def test_read_file_multiple_columns(self, tmp_path):
        # Arrange
        path = tmp_path / "multiple_columns.csv"
        test_df = self.write_dummy_csv(
            path, headers=False, datetime_format="%Y-%m-%d %H:%M:%S", num_columns=2
        )

        # Act
        df = Event.read_csv(path)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert isinstance(df.index, pd.DatetimeIndex)

        pd.testing.assert_frame_equal(df, test_df)
