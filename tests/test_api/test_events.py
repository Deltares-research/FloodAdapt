from pathlib import Path

import pytest

import flood_adapt.api.events as api_events
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_synthetic_event():
    test_dict = {
        "name": "extreme12ft",
        "long_name": "extreme 12 foot event",
        "mode": "single_event",
        "template": "Synthetic",
        "timing": "idealized",
        "water_level_offset": {"value": "zero", "units": "feet"},
        "wind": {
            "source": "constant",
            "constant_speed": {"value": 0, "units": "m/s"},
            "constant_direction": {"value": 0, "units": "deg N"},
        },
        "rainfall": {"source": "none"},
        "river": {
            "source": "constant",
            "constant_discharge": {"value": 5000, "units": "cfs"},
        },
        "time": {"duration_before_t0": 24, "duration_after_t0": "24"},
        "tide": {
            "source": "harmonic",
            "harmonic_amplitude": {"value": 3, "units": "feet"},
        },
        "surge": {
            "source": "shape",
            "shape_type": "gaussian",
            "shape_duration": 24,
            "shape_peak_time": 0,
            "shape_peak": {"value": 9.22, "units": "feet"},
        },
    }
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    # When user presses add event and chooses the events
    # the dictionary is returned and an Event object is created
    with pytest.raises(ValueError):
        # Assert error if a value is incorrect
        event = api_events.create_synthetic_event(test_dict)

    # correct event
    test_dict["water_level_offset"]["value"] = 0
    event = api_events.create_synthetic_event(test_dict)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_events.save_event_toml(event, database)

    # Change name to something new
    test_dict["name"] = "test1"
    event = api_events.create_synthetic_event(test_dict)
    # If the name is not used before the measure is save in the database
    api_events.save_event_toml(event, database)
    database.get_events()

    # Try to delete a measure which is already used in a scenario
    # with pytest.raises(ValueError):
    #    api_events.delete_measure("", database)

    # If user presses delete event the measure is deleted
    api_events.delete_event("test1", database)
    database.get_events()
