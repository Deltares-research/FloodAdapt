import datetime

import pytest

import flood_adapt.api.events as api_events
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulTime


@pytest.fixture()
def test_dict():
    test_dict = {
        "name": "extreme12ft",
        "description": "extreme 12 foot event",
        "mode": "single_event",
        "template": "Synthetic",
        "timing": "idealized",
        "water_level_offset": {"value": 0, "units": "feet"},
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
            "shape_type": "gaussian",
            "shape_duration": 24,
            "shape_peak_time": 0,
            "shape_peak": {"value": 9.22, "units": "feet"},
        },
    }
    yield test_dict


def test_create_synthetic_event_valid_dict(test_db, test_dict):
    # When user presses add event and chooses the events
    # the dictionary is returned and an Event object is created
    api_events.create_synthetic_event(test_dict)
    # TODO assert event attrs


def test_create_synthetic_event_invalid_dict(test_db, test_dict):
    del test_dict["name"]
    with pytest.raises(ValueError):
        # Assert error if a value is incorrect
        api_events.create_synthetic_event(test_dict)
    # TODO assert error msg


TimeModel(
    start_time=datetime.datetime(year=2024, month=10, day=1),
    end_time=datetime.datetime(year=2024, month=10, day=3),
    time_step=UnitfulTime(value=1, units="hours").to_timedelta(),
).model_dump()


def test_save_synthetic_event_already_exists(test_db, test_dict):
    event = api_events.create_synthetic_event(test_dict)
    if test_dict["name"] not in api_events.get_events()["name"]:
        api_events.save_event_toml(event)

    with pytest.raises(ValueError):
        api_events.save_event_toml(event)
    # TODO assert error msg


def test_save_event_toml_valid(test_db, test_dict):
    # Change name to something new
    test_dict["name"] = "testNew"
    event = api_events.create_synthetic_event(test_dict)
    if test_dict["name"] in api_events.get_events()["name"]:
        api_events.delete_event(test_dict["name"])
    api_events.save_event_toml(event)
    # TODO assert event attrs


def test_delete_event_doesnt_exist(test_db):
    # apparently this doesnt raise an error?
    api_events.delete_event("doesnt_exist")
