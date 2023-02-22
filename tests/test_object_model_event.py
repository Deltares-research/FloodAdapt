from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_create_new_event():
    from flood_adapt.object_model.hazard.event.synthetic import Synthetic
    from flood_adapt.object_model.hazard.event.event import Event

    test_event = Event()

    # assert that attributes have been set to correct default value data types
    assert test_event
    assert isinstance(test_event.name, str)
    assert isinstance(test_event.long_name, str)
    assert isinstance(test_event.template, str)
    assert isinstance(test_event.timing, str)
    assert isinstance(test_event.water_level_offset, dict)
    assert isinstance(test_event.tide, dict)
    assert isinstance(test_event.surge, dict)
    assert isinstance(test_event.wind, dict)
    assert isinstance(test_event.rainfall, dict)
    assert isinstance(test_event.river, dict)

def test_read_config_synthetic():
    from flood_adapt.object_model.hazard.event.synthetic import Synthetic

    test_toml = test_database / "charleston" / "input" / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()

    test_synthetic = Synthetic(test_toml)
    test_synthetic.load()

    # assert that attributes have been set to correct data types
    assert test_synthetic
    assert isinstance(test_synthetic.name, str)
    assert isinstance(test_synthetic.long_name, str)
    assert isinstance(test_synthetic.template, str)
    assert isinstance(test_synthetic.timing, str)
    assert isinstance(test_synthetic.duration_before_t0, int)
    assert isinstance(test_synthetic.duration_after_t0, int)
    assert isinstance(test_synthetic.water_level_offset, dict)
    assert isinstance(test_synthetic.tide, dict)
    assert isinstance(test_synthetic.surge, dict)
    assert isinstance(test_synthetic.wind, dict)
    assert isinstance(test_synthetic.rainfall, dict)
    assert isinstance(test_synthetic.river, dict)

    # assert that attributes have been set to values from toml file
    assert test_synthetic
    assert test_synthetic.name == "extreme12ft"
    assert test_synthetic.long_name == "extreme 12 foot event"
    assert test_synthetic.template == "Synthetic"
    assert test_synthetic.timing == "idealized"
    assert test_synthetic.duration_before_t0 == 24
    assert test_synthetic.duration_after_t0 == 24
    assert test_synthetic.water_level_offset["value"] == 0
    assert test_synthetic.water_level_offset["units"] == "feet"
    assert test_synthetic.tide["source"] == "harmonic"
    assert test_synthetic.tide["harmonic_amplitude"]["value"] == 3
    assert test_synthetic.tide["harmonic_amplitude"]["units"] == "feet"
    assert test_synthetic.surge["source"] == "shape"
    assert test_synthetic.surge["shape_type"] == "gaussian"
    assert test_synthetic.surge["shape_peak"]["value"] == 9.22
    assert test_synthetic.surge["shape_peak"]["units"] == "feet"
    assert test_synthetic.surge["shape_duration"] == 24
    assert test_synthetic.surge["shape_peak_time"] == 0
    assert test_synthetic.surge["panel_text"] == "Storm Surge"
    assert test_synthetic.wind["source"] == "constant"
    assert test_synthetic.wind["constant_speed"]["value"] == 0
    assert test_synthetic.wind["constant_speed"]["units"] == "m/s"
    assert test_synthetic.wind["constant_direction"]["value"] == 0
    assert test_synthetic.wind["constant_direction"]["units"] == "deg N"
    assert test_synthetic.rainfall["source"] == "none"
    assert test_synthetic.river["source"] == "constant"
    assert test_synthetic.river["constant_discharge"]["value"] == 5000
    assert test_synthetic.river["constant_discharge"]["units"] == "cfs"


def test_create_new_synthetic():
    from flood_adapt.object_model.hazard.event.synthetic import Synthetic

    test_synthetic = Synthetic()

    # assert that attributes have been set to correct default value data types
    assert test_synthetic
    assert isinstance(test_synthetic.name, str)
    assert isinstance(test_synthetic.long_name, str)
    assert isinstance(test_synthetic.template, str)
    assert isinstance(test_synthetic.timing, str)
    assert isinstance(test_synthetic.duration_before_t0, int)
    assert isinstance(test_synthetic.duration_after_t0, int)
    assert isinstance(test_synthetic.water_level_offset, dict)
    assert isinstance(test_synthetic.tide, dict)
    assert isinstance(test_synthetic.surge, dict)
    assert isinstance(test_synthetic.wind, dict)
    assert isinstance(test_synthetic.rainfall, dict)
    assert isinstance(test_synthetic.river, dict)