from pathlib import Path

import tomli

from flood_adapt.object_model.hazard.event.event import Mode, Template, Timing
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.synthetic import (
    TideModel,
    TimeModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength

test_database = Path().absolute() / "tests" / "test_database"


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
        toml = tomli.load(fp)

    # use event template to get the associated Event child class
    template = toml["template"]
    test_synthetic = EventFactory.get_event(template).load_file(test_toml)

    # assert that attributes have been set to correct data types
    assert test_synthetic
    assert isinstance(test_synthetic.model.name, str)
    assert isinstance(test_synthetic.model.long_name, str)
    assert isinstance(test_synthetic.model.mode, Mode)
    assert isinstance(test_synthetic.model.template, Template)
    assert isinstance(test_synthetic.model.timing, Timing)
    assert isinstance(test_synthetic.model.water_level_offset, UnitfulLength)
    assert isinstance(test_synthetic.model.time, TimeModel)
    assert isinstance(test_synthetic.model.tide, TideModel)
    # assert isinstance(test_synthetic.model.surge, dict)
    # assert isinstance(test_synthetic.model.wind, dict)
    # assert isinstance(test_synthetic.model.rainfall, dict)
    # assert isinstance(test_synthetic.model.river, dict)

    # assert that attributes have been set to values from toml file
    assert test_synthetic.model
    assert test_synthetic.model.name == "extreme12ft"
    assert test_synthetic.model.long_name == "extreme 12 foot event"
    assert test_synthetic.model.template == "Synthetic"
    assert test_synthetic.model.timing == "idealized"
    assert test_synthetic.model.water_level_offset.value == 0
    assert test_synthetic.model.water_level_offset.units == "feet"
    assert test_synthetic.model.time.duration_before_t0 == 24.0
    assert test_synthetic.model.time.duration_after_t0 == 24.0
    assert test_synthetic.model.tide.source == "harmonic"
    assert test_synthetic.model.tide.harmonic_amplitude.value == 3
    assert test_synthetic.model.tide.harmonic_amplitude.units == "feet"
    # assert test_synthetic.model.surge["source"] == "shape"
    # assert test_synthetic.model.surge["shape_type"] == "gaussian"
    # assert test_synthetic.model.surge["shape_peak"]["value"] == 9.22
    # assert test_synthetic.model.surge["shape_peak"]["units"] == "feet"
    # assert test_synthetic.model.surge["shape_duration"] == 24
    # assert test_synthetic.model.surge["shape_peak_time"] == 0
    # assert test_synthetic.model.surge["panel_text"] == "Storm Surge"
    # assert test_synthetic.model.wind["source"] == "constant"
    # assert test_synthetic.model.wind["constant_speed"]["value"] == 0
    # assert test_synthetic.model.wind["constant_speed"]["units"] == "m/s"
    # assert test_synthetic.model.wind["constant_direction"]["value"] == 0
    # assert test_synthetic.model.wind["constant_direction"]["units"] == "deg N"
    # assert test_synthetic.model.rainfall["source"] == "none"
    # assert test_synthetic.model.river["source"] == "constant"
    # assert test_synthetic.model.river["constant_discharge"]["value"] == 5000
    # assert test_synthetic.model.river["constant_discharge"]["units"] == "cfs"

    # ensure it's saving a file
    test_synthetic.save(test_save_toml)
