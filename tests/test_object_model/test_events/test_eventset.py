from datetime import datetime
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.synthetic import SyntheticEvent
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesVelocity,
)


@pytest.fixture()
def test_eventset_model():
    attrs = {
        "name": "test_eventset_synthetic",
        "time": TimeModel(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        "template": Template.Synthetic,
        "mode": Mode.risk,
        "sub_events": ["event_0001", "event_0039", "event_0078"],
        "frequency": [0.5, 0.2, 0.02],
        "forcings": {
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeConstant(
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type="triangle",
                        duration=UnitfulTime(value=1, units="days"),
                        peak_time=UnitfulTime(value=8, units="hours"),
                        peak_value=UnitfulLength(value=1, units="meters"),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(value=1, units="meters"),
                    harmonic_period=UnitfulTime(value=12.4, units="hours"),
                    harmonic_phase=UnitfulTime(value=0, units="hours"),
                ),
            ),
        },
    }
    return attrs


class TestEventSet:
    @pytest.fixture()
    def test_synthetic_eventset(self, test_eventset_model: dict[str, Any]):
        return EventSet.load_dict(test_eventset_model)

    @pytest.fixture()
    def test_scenario(self, test_db, test_synthetic_eventset: EventSet):
        test_db.events.save(test_synthetic_eventset)

        scn = test_db.scenarios.get("current_test_set_synthetic_no_measures")

        return test_db, scn, test_synthetic_eventset

    def test_get_subevent_paths(self, test_db, test_synthetic_eventset: EventSet):
        subevent_paths = test_synthetic_eventset.get_sub_event_paths()
        assert len(subevent_paths) == len(test_synthetic_eventset.attrs.sub_events)

    def test_get_subevents_create_sub_events(
        self, test_db, test_synthetic_eventset: EventSet
    ):
        subevent_paths = test_synthetic_eventset.get_sub_event_paths()

        subevents = test_synthetic_eventset.get_subevents()

        assert len(subevents) == len(test_synthetic_eventset.attrs.sub_events)
        assert all(subevent_path.exists() for subevent_path in subevent_paths)

        assert test_synthetic_eventset.attrs.mode == Mode.risk
        assert all(subevent.attrs.mode == Mode.single_event for subevent in subevents)

    def test_eventset_synthetic_process(self, test_scenario: tuple):
        test_db, scn, test_eventset = test_scenario
        SyntheticEvent.process = mock.Mock()
        test_eventset.process(scn)

        assert SyntheticEvent.process.call_count == len(test_eventset.attrs.sub_events)

    def test_calculate_rp_floodmaps(self, test_scenario: tuple):
        test_db, scn, test_eventset = test_scenario

        scn.run()
        output_path = (
            Path(test_db.scenarios.get_database_path(get_input_path=False))
            / scn.attrs.name
            / "Flooding"
        )

        for rp in test_db.site.attrs.risk.return_periods:
            assert (output_path / f"RP_{rp:04d}_maps.nc").exists()
            assert (output_path / f"RP_{rp:04d}_maps.tif").exists()
