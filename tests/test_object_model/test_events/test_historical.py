from datetime import datetime

import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesVelocity,
)


class TestHistoricalEvent:
    @pytest.fixture()
    def test_event_attrs(self):
        attrs = {
            "name": "test_historical",
            "time": TimeModel(
                start_time=datetime(2020, 1, 1),
                end_time=datetime(2020, 1, 2),
            ),
            "template": Template.Historical,
            "mode": Mode.single_event,
            "forcings": {
                "WIND": WindConstant(
                    speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                    direction=UnitfulDirection(
                        value=60, units=UnitTypesDirection.degrees
                    ),
                ),
                "RAINFALL": RainfallConstant(
                    intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
                ),
                "DISCHARGE": DischargeConstant(
                    discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
                ),
                "WATERLEVEL": WaterlevelFromGauged(path="path/to/gauged_data"),
            },
        }
        return attrs

    def test_save_event_toml(self, test_event_attrs, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = HistoricalEvent.load_dict(test_event_attrs)
        test_event.save(path)
        assert path.exists()

    def test_load_dict(self, test_event_attrs):
        loaded_event = HistoricalEvent.load_dict(test_event_attrs)

        assert loaded_event.attrs.name == test_event_attrs["name"]
        assert loaded_event.attrs.time == test_event_attrs["time"]
        assert loaded_event.attrs.template == test_event_attrs["template"]
        assert loaded_event.attrs.mode == test_event_attrs["mode"]
        assert loaded_event.attrs.forcings == test_event_attrs["forcings"]

    def test_load_file(self, test_event_attrs, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = HistoricalEvent.load_dict(test_event_attrs)
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        assert loaded_event == saved_event
