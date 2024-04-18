import pytest

import flood_adapt.api.events as api_events
from flood_adapt.object_model.interface.events import ShapeType


@pytest.fixture(scope="session")
def test_dict():
    test_dict = {
        "name": "extreme12ft",
        "description": "extreme 12 foot event",
        "mode": "single_event",
        "timing": "idealized",
        "water_level_offset": {"value": "zero", "units": "feet"},
        "wind": {
            "source": "constant",
            "constant_speed": {"value": 0, "units": "m/s"},
            "constant_direction": {"value": 0, "units": "deg N"},
        },
        "rainfall": {"source": "none"},
        "river": [
            {
                "source": "constant",
                "constant_discharge": {"value": 5000, "units": "cfs"},
            }
        ],
        "time": {"duration_before_t0": 24, "duration_after_t0": "24"},
        "tide": {
            "source": "harmonic",
            "harmonic_amplitude": {"value": 3, "units": "feet"},
        },
        "surge": {
            "source": "shape",
            "shape_type": ShapeType.gaussian,
            "shape_duration": 24,
            "shape_peak_time": 0,
            "shape_peak": {"value": 9.22, "units": "feet"},
        },
    }
    return test_dict


def test_synthetic_event(test_db, test_dict):
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
        api_events.save_event_toml(event, test_db)

    # Change name to something new
    test_dict["name"] = "test1"
    event = api_events.create_synthetic_event(test_dict)
    # If the name is not used before the measure is save in the database
    api_events.save_event_toml(event, test_db)
    test_db.get_events()

    # Try to delete a measure which is already used in a scenario
    # with pytest.raises(ValueError):
    #    api_events.delete_measure("", database)

    # If user presses delete event the measure is deleted
    api_events.delete_event("test1", test_db)
    test_db.get_events()
