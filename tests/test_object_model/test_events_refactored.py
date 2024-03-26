from flood_adapt.object_model.hazard.event.event import Event


class TestEvent:
    _TIME_MODEL = {
        "timing": "idealized",
        "duration_before_t0": {
            "value": 0,
            "units": "hours",
        },
        "duration_after_t0": {
            "value": 10,
            "units": "hours",
        },
        "start_time": "2020-01-01 00:00:00",
        "end_time": "2020-01-03 00:00:00",
    }

    _TIMESERIES_MODEL = {
        "shape_type": "constant",
        "start_time": {
            "value": 0,
            "units": "hours",
        },
        "end_time": {
            "value": 10,
            "units": "hours",
        },
        "peak_intensity": {
            "value": 1,
            "units": "mm/hr",
        },
    }

    _RIVER_MODEL = {
        "timeseries": _TIMESERIES_MODEL,
        "base_discharge": {
            "value": 100,
            "units": "m3/s",
        },
    }

    _WIND_MODEL = {
        "source": "constant",
        "constant_speed": {
            "value": 1,
            "units": "m/s",
        },
        "constant_direction": {
            "value": 90,
            "units": "deg N",
        },
    }

    _TIDE_MODEL = {
        "source": "timeseries",
        "timeseries": _TIMESERIES_MODEL,
    }

    _SURGE_MODEL = {
        "source": "timeseries",
        "timeseries": _TIMESERIES_MODEL,
    }

    _RAINFALL_MODEL = {
        "source": "timeseries",
        "timeseries": _TIMESERIES_MODEL,
        "increase": 20,
    }

    _TRANSLATION_MODEL = {
        "eastwest_translation": {
            "value": 20,
            "units": "meters",
        },
        "northsouth_translation": {
            "value": 10,
            "units": "meters",
        },
    }

    _HURRICANE_MODEL = {
        "track_name": "test_track",
        "hurricane_translation": _TRANSLATION_MODEL,
    }

    _OVERLAND_MODEL = {
        "river": [
            _RIVER_MODEL,
            _RIVER_MODEL,
        ],
        "rainfall": _RAINFALL_MODEL,
    }

    _OFFSHORE_MODEL = {
        "wind": _WIND_MODEL,
        "tide": _TIDE_MODEL,
        "surge": _SURGE_MODEL,
        "hurricane": _HURRICANE_MODEL,
    }

    _EVENT_MODEL = {
        "name": "test_event",
        "description": "test_description",
        "mode": "single_event",
        "time": _TIME_MODEL,
        "overland": _OVERLAND_MODEL,
        "offshore": _OFFSHORE_MODEL,
        "water_level_offset": {
            "value": 2,
            "units": "meters",
        },
    }

    def test_load_dict(self):
        # Call the load_dict method
        event = Event().load_dict(self._EVENT_MODEL)

    def test_add_rainfall_ts(self):
        # Create an Event object
        event = Event().load_dict(self._EVENT_MODEL)

        # Call the add_rainfall_ts method
        event = event.add_rainfall_ts()
