from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from unittest.mock import patch

import object_model.io.unitfulvalue as uv
import pytest
from dbs_classes.interface.database import IDatabase
from object_model.hazard.event.event_factory import EventFactory
from object_model.hazard.event.event_set import EventSet
from object_model.hazard.event.forcing.discharge import DischargeConstant
from object_model.hazard.event.forcing.rainfall import RainfallConstant
from object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from object_model.hazard.event.forcing.wind import WindConstant
from object_model.hazard.interface.models import (
    Mode,
    ShapeType,
    Template,
    TimeModel,
)
from object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from object_model.interface.events import IEventModel
from object_model.interface.site import RiverModel
from object_model.scenario import Scenario


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
                speed=uv.UnitfulVelocity(value=5, units=uv.UnitTypesVelocity.mps),
                direction=uv.UnitfulDirection(
                    value=60, units=uv.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=uv.UnitfulIntensity(
                    value=20, units=uv.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": DischargeConstant(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=uv.UnitfulDischarge(
                        value=5000, units=uv.UnitTypesDischarge.cfs
                    ),
                ),
                discharge=uv.UnitfulDischarge(
                    value=5000, units=uv.UnitTypesDischarge.cfs
                ),
            ),
            "WATERLEVEL": WaterlevelSynthetic(
                surge=SurgeModel(
                    timeseries=SyntheticTimeseriesModel(
                        shape_type=ShapeType.triangle,
                        duration=uv.UnitfulTime(value=1, units=uv.UnitTypesTime.days),
                        peak_time=uv.UnitfulTime(value=8, units=uv.UnitTypesTime.hours),
                        peak_value=uv.UnitfulLength(
                            value=1, units=uv.UnitTypesLength.meters
                        ),
                    )
                ),
                tide=TideModel(
                    harmonic_amplitude=uv.UnitfulLength(
                        value=1, units=uv.UnitTypesLength.meters
                    ),
                    harmonic_period=uv.UnitfulTime(
                        value=12.4, units=uv.UnitTypesTime.hours
                    ),
                    harmonic_phase=uv.UnitfulTime(
                        value=0, units=uv.UnitTypesTime.hours
                    ),
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

    @patch("flood_adapt.object_model.hazard.event.synthetic.SyntheticEvent.preprocess")
    def test_eventset_synthetic_process(
        self,
        mock_process,
        setup_eventset_scenario: tuple[IDatabase, Scenario, EventSet],
        tmp_path: Path,
    ):
        test_db, scn, event_set = setup_eventset_scenario
        output_dir = tmp_path / "eventset"
        event_set.preprocess(output_dir)

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
