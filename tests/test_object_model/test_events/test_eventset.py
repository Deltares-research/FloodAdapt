import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

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
from flood_adapt.object_model.hazard.interface.models import (
    Mode,
    ShapeType,
    Template,
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.database import IDatabase
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
    UnitTypesLength,
    UnitTypesTime,
    UnitTypesVelocity,
)
from flood_adapt.object_model.scenario import Scenario


@pytest.fixture()
def test_eventset():
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
                        shape_type=ShapeType.triangle,
                        duration=UnitfulTime(value=1, units=UnitTypesTime.days),
                        peak_time=UnitfulTime(value=8, units=UnitTypesTime.hours),
                        peak_value=UnitfulLength(value=1, units=UnitTypesLength.meters),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=UnitfulLength(
                        value=1, units=UnitTypesLength.meters
                    ),
                    harmonic_period=UnitfulTime(value=12.4, units=UnitTypesTime.hours),
                    harmonic_phase=UnitfulTime(value=0, units=UnitTypesTime.hours),
                ),
            ),
        },
    }
    return EventSet.load_dict(attrs)


@pytest.fixture()
def test_db_with_dummyscn_and_eventset(
    test_db: IDatabase,
    test_eventset,
    dummy_pump_measure,
    dummy_buyout_measure,
    dummy_projection,
    dummy_strategy,
):
    pump, geojson = dummy_pump_measure
    dst_path = test_db.measures.get_database_path() / pump.attrs.name / geojson.name
    test_db.measures.save(pump)
    shutil.copy2(geojson, dst_path)

    test_db.measures.save(dummy_buyout_measure)

    test_db.projections.save(dummy_projection)
    test_db.strategies.save(dummy_strategy)

    event_set = test_eventset
    test_db.events.save(event_set)

    scn = Scenario.load_dict(
        {
            "name": "test_eventset",
            "event": event_set.attrs.name,
            "projection": dummy_projection.attrs.name,
            "strategy": dummy_strategy.attrs.name,
        }
    )
    test_db.scenarios.save(scn)

    return test_db, scn, event_set


class TestEventSet:
    def test_get_subevent_paths(self, test_db, test_eventset: EventSet):
        subevent_paths = test_eventset.get_sub_event_paths()
        assert len(subevent_paths) == len(test_eventset.attrs.sub_events)

    def test_get_subevents_create_sub_events(self, test_db, test_eventset: EventSet):
        subevent_paths = test_eventset.get_sub_event_paths()

        subevents = test_eventset.get_subevents()

        assert len(subevents) == len(test_eventset.attrs.sub_events)
        assert all(subevent_path.exists() for subevent_path in subevent_paths)

        assert test_eventset.attrs.mode == Mode.risk
        assert all(subevent.attrs.mode == Mode.single_event for subevent in subevents)

    @patch("flood_adapt.object_model.hazard.event.synthetic.SyntheticEvent.process")
    def test_eventset_synthetic_process(
        self,
        mock_process,
        test_db_with_dummyscn_and_eventset: tuple[IDatabase, Scenario, EventSet],
    ):
        test_db, scn, event_set = test_db_with_dummyscn_and_eventset
        event_set.process(scn)

        assert mock_process.call_count == len(event_set.attrs.sub_events)

    def test_calculate_rp_floodmaps(self, test_db_with_dummyscn_and_eventset: tuple):
        test_db, scn, event_set = test_db_with_dummyscn_and_eventset

        scn.run()
        output_path = (
            Path(test_db.scenarios.get_database_path(get_input_path=False))
            / scn.attrs.name
            / "Flooding"
        )

        for rp in test_db.site.attrs.risk.return_periods:
            assert (output_path / f"RP_{rp:04d}_maps.nc").exists()
            assert (output_path / f"RP_{rp:04d}_maps.tif").exists()
