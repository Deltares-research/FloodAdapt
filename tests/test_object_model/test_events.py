import unittest
from datetime import datetime
from pathlib import Path

import tomli

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.historical_offshore import HistoricalOffshore
from flood_adapt.object_model.interface.events import (
    Mode,
    Template,
    TideModel,
    TimeModel,
    Timing,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength
from flood_adapt.object_model.site import (
    Site,
)

test_database = Path().absolute() / "tests" / "test_database"


class TestEvent(unittest.TestCase):
    def test_get_template(self):
        # test that it can find the template
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

    def test_load_from_toml_synthetic(self):
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

    def test_save_to_toml_synthetic(self):
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

    def test_load_from_toml_hurricane(self):
        test_toml = (
            test_database / "charleston" / "input" / "events" / "ETA" / "ETA.toml"
        )

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
        assert test_synthetic.attrs.name == "ETA"
        assert test_synthetic.attrs.long_name == "ETA"
        assert test_synthetic.attrs.template == "Historical - hurricane"
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

    def test_save_to_toml_hurricane(self):
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
    assert wl_df.iloc[:,0].dtypes == "float64"
