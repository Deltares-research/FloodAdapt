from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from unittest.mock import patch

import pytest

from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.interface.events import IEventModel
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
from flood_adapt.object_model.interface.site import RiverModel
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
def test_sub_event():
    return {
        "time": TimeModel(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        "template": Template.Synthetic,
        "mode": Mode.single_event,
        "forcings": {
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=UnitfulDischarge(
                        value=5000, units=UnitTypesDischarge.cfs
                    ),
                ),
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs),
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


@pytest.fixture()
def test_eventset(test_sub_event) -> tuple[EventSet, list[IEventModel]]:
    sub_events: list[IEventModel] = []
    for i in [1, 39, 78]:
        test_sub_event["name"] = f"subevent_{i:04d}"
        sub_events.append(EventFactory.load_dict(test_sub_event).attrs)

    attrs = {
        "name": "test_eventset_synthetic",
        "mode": Mode.risk,
        "sub_events": sub_events,
        "frequency": [0.5, 0.2, 0.02],
    }
    return EventSet.load_dict(attrs), sub_events


@pytest.fixture()
def setup_eventset_scenario(
    test_db: IDatabase,
    test_eventset,
    # dummy_pump_measure,
    # dummy_buyout_measure,
    dummy_projection,
    dummy_strategy,
):
    # test_db.measures.save(dummy_pump_measure)
    # test_db.measures.save(dummy_buyout_measure)
    test_db.projections.save(dummy_projection)
    test_db.strategies.save(dummy_strategy)

    test_eventset, sub_events = test_eventset
    test_db.events.save(test_eventset)

    scn = Scenario.load_dict(
        {
            "name": "test_eventset",
            "event": test_eventset.attrs.name,
            "projection": dummy_projection.attrs.name,
            "strategy": dummy_strategy.attrs.name,
        }
    )
    test_db.scenarios.save(scn)

    return test_db, scn, test_eventset


class TestEventSet:
    def test_save_all_sub_events(
        self, test_eventset: tuple[EventSet, list[IEventModel]]
    ):
        event_set, _ = test_eventset

        tmp_path = Path(gettempdir()) / "test_eventset.toml"
        event_set.save_additional(output_dir=tmp_path.parent)

        for sub_event in event_set.attrs.sub_events:
            assert (
                tmp_path.parent / sub_event.name / f"{sub_event.name}.toml"
            ).exists()

    @patch("flood_adapt.object_model.hazard.event.synthetic.SyntheticEvent.process")
    def test_eventset_synthetic_process(
        self,
        mock_process,
        setup_eventset_scenario: tuple[IDatabase, Scenario, EventSet],
    ):
        test_db, scn, event_set = setup_eventset_scenario
        event_set.process(scn)

        assert mock_process.call_count == len(event_set.attrs.sub_events)

    def test_calculate_rp_floodmaps(
        self, setup_eventset_scenario: tuple[IDatabase, Scenario, EventSet]
    ):
        test_db, scn, event_set = setup_eventset_scenario

        scn.run()
        output_path = Path(test_db.scenarios.output_path) / scn.attrs.name / "Flooding"

        for rp in test_db.site.attrs.risk.return_periods:
            assert (output_path / f"RP_{rp:04d}_maps.nc").exists()
            assert (output_path / f"RP_{rp:04d}_maps.tif").exists()