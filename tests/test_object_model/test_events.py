from pathlib import Path
import tomli

from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.io.unitfulvalue import UnitfulValue
from flood_adapt.object_model.hazard.event.synthetic import TideModel, TimeModel
from flood_adapt.object_model.hazard.event.event import Mode, Template, Timing
from flood_adapt.object_model.hazard.event.event_factory import EventFactory

test_database = Path().absolute() / "tests" / "test_database"


def test_create_new_event():
    test_event = Synthetic()

    # assert that attributes have been set to correct default value data types
    assert test_event
    assert isinstance(test_event.event_generic.name, str)
    assert isinstance(test_event.event_generic.long_name, str)
    assert isinstance(test_event.event_generic.template, str)
    assert isinstance(test_event.event_generic.timing, str)
    assert isinstance(test_event.event_generic.water_level_offset, UnitfulValue)
    assert isinstance(test_event.synthetic.tide, TideModel)
    # assert isinstance(test_event.surge, dict)
    # assert isinstance(test_event.wind, dict)
    # assert isinstance(test_event.rainfall, dict)
    # assert isinstance(test_event.river, dict)


def test_create_new_synthetic():
    test_synthetic = Synthetic()

    # assert that attributes have been set to correct default value data types
    assert test_synthetic
    assert isinstance(test_synthetic.event_generic.name, str)
    assert isinstance(test_synthetic.event_generic.long_name, str)
    assert isinstance(test_synthetic.event_generic.template, str)
    assert isinstance(test_synthetic.event_generic.timing, str)
    assert isinstance(test_synthetic.event_generic.water_level_offset, UnitfulValue)
    assert isinstance(test_synthetic.synthetic.time.duration_before_t0, float)
    assert isinstance(test_synthetic.synthetic.time.duration_after_t0, float)
    assert isinstance(test_synthetic.synthetic.tide, TideModel)
    # assert isinstance(test_synthetic.surge, dict)
    # assert isinstance(test_synthetic.wind, dict)
    # assert isinstance(test_synthetic.rainfall, dict)
    # assert isinstance(test_synthetic.river, dict)


def test_read_config_synthetic():
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
        toml = tomli.load(fp)

    # use event template to get the associated Event child class
    template = toml["template"]
    test_synthetic = EventFactory.get_event(template).load(test_toml)

    # assert that attributes have been set to correct data types
    assert test_synthetic
    assert isinstance(test_synthetic.event_generic.name, str)
    assert isinstance(test_synthetic.event_generic.long_name, str)
    assert isinstance(test_synthetic.event_generic.mode, Mode)
    assert isinstance(test_synthetic.event_generic.template, Template)
    assert isinstance(test_synthetic.event_generic.timing, Timing)
    assert isinstance(test_synthetic.event_generic.water_level_offset, UnitfulValue)
    assert isinstance(test_synthetic.synthetic.time, TimeModel)
    assert isinstance(test_synthetic.synthetic.tide, TideModel)
    # assert isinstance(test_synthetic.surge, dict)
    # assert isinstance(test_synthetic.wind, dict)
    # assert isinstance(test_synthetic.rainfall, dict)
    # assert isinstance(test_synthetic.river, dict)

    # assert that attributes have been set to values from toml file
    assert test_synthetic
    assert test_synthetic.event_generic.name == "extreme12ft"
    assert test_synthetic.event_generic.long_name == "extreme 12 foot event"
    assert test_synthetic.event_generic.template == "Synthetic"
    assert test_synthetic.event_generic.timing == "idealized"
    assert test_synthetic.event_generic.water_level_offset.value == 0
    assert test_synthetic.event_generic.water_level_offset.units == "feet"
    assert test_synthetic.synthetic.time.duration_before_t0 == 24.0
    assert test_synthetic.synthetic.time.duration_after_t0 == 24.0
    assert test_synthetic.synthetic.tide.source == "harmonic"
    assert test_synthetic.synthetic.tide.harmonic_amplitude.value == 3
    assert test_synthetic.synthetic.tide.harmonic_amplitude.units == "feet"
    # assert test_synthetic.surge["source"] == "shape"
    # assert test_synthetic.surge["shape_type"] == "gaussian"
    # assert test_synthetic.surge["shape_peak"]["value"] == 9.22
    # assert test_synthetic.surge["shape_peak"]["units"] == "feet"
    # assert test_synthetic.surge["shape_duration"] == 24
    # assert test_synthetic.surge["shape_peak_time"] == 0
    # assert test_synthetic.surge["panel_text"] == "Storm Surge"
    # assert test_synthetic.wind["source"] == "constant"
    # assert test_synthetic.wind["constant_speed"]["value"] == 0
    # assert test_synthetic.wind["constant_speed"]["units"] == "m/s"
    # assert test_synthetic.wind["constant_direction"]["value"] == 0
    # assert test_synthetic.wind["constant_direction"]["units"] == "deg N"
    # assert test_synthetic.rainfall["source"] == "none"
    # assert test_synthetic.river["source"] == "constant"
    # assert test_synthetic.river["constant_discharge"]["value"] == 5000
    # assert test_synthetic.river["constant_discharge"]["units"] == "cfs"
