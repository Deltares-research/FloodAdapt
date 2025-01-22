from datetime import datetime
from pathlib import Path
from tempfile import gettempdir
from unittest.mock import patch

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.interface.events import (
    Mode,
    Template,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ShapeType,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.io import unit_system as us
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
            "WIND": [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                ).model_dump()
            ],
            "RAINFALL": [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=2, units=us.UnitTypesIntensity.mm_hr
                    )
                ).model_dump()
            ],
            "DISCHARGE": [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                ).model_dump(),
            ],
            "WATERLEVEL": [
                WaterlevelSynthetic(
                    surge=SurgeModel(
                        timeseries=SyntheticTimeseriesModel[us.UnitfulLength](
                            shape_type=ShapeType.triangle,
                            duration=us.UnitfulTime(
                                value=1, units=us.UnitTypesTime.days
                            ),
                            peak_time=us.UnitfulTime(
                                value=8, units=us.UnitTypesTime.hours
                            ),
                            peak_value=us.UnitfulLength(
                                value=1, units=us.UnitTypesLength.meters
                            ),
                        )
                    ),
                    tide=TideModel(
                        harmonic_amplitude=us.UnitfulLength(
                            value=1, units=us.UnitTypesLength.meters
                        ),
                        harmonic_phase=us.UnitfulTime(
                            value=0, units=us.UnitTypesTime.hours
                        ),
                    ),
                ).model_dump()
            ],
        },
    }


@pytest.fixture()
def test_eventset(test_sub_event) -> EventSet:
    sub_events = []
    for i in [1, 39, 78]:
        test_sub_event["name"] = f"subevent_{i:04d}"
        sub_events.append(test_sub_event.copy())

    attrs = {
        "name": "test_eventset_synthetic",
        "mode": Mode.risk,
        "sub_events": sub_events,
        "frequency": [0.5, 0.2, 0.02],
    }
    return EventSet.load_dict(attrs)


def test_save_reload_eventset(test_eventset: EventSet, tmp_path: Path):
    path = tmp_path / f"{test_eventset.attrs.name}.toml"
    test_eventset.save(path)
    reloaded = EventSet.load_file(path)

    assert reloaded == test_eventset


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
    def test_save_all_sub_events(self, test_eventset: EventSet):
        tmp_path = Path(gettempdir()) / "test_eventset.toml"
        test_eventset.save_additional(output_dir=tmp_path.parent)

        for sub_event in test_eventset.attrs.sub_events:
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

        for rp in test_db.site.attrs.fiat.risk.return_periods:
            assert (output_path / f"RP_{rp:04d}_maps.nc").exists()
            assert (output_path / f"RP_{rp:04d}_maps.tif").exists()
