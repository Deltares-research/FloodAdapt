import platform
from pathlib import Path
from tempfile import gettempdir

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.objects.events.event_set import (
    EventSet,
)
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.scenario_runner import ScenarioRunner


def test_save_reload_eventset(test_eventset: EventSet, tmp_path: Path):
    path = tmp_path / f"{test_eventset.name}.toml"
    test_eventset.save(path)
    reloaded = EventSet.load_file(path)

    assert reloaded == test_eventset


class TestEventSet:
    def test_save_all_sub_events(self, test_eventset: EventSet):
        tmp_path = Path(gettempdir()) / "test_eventset.toml"
        test_eventset.save_additional(output_dir=tmp_path.parent)

        for sub_event in test_eventset.sub_events:
            assert (
                tmp_path.parent / sub_event.name / f"{sub_event.name}.toml"
            ).exists()

    @pytest.mark.skipif(
        platform.system() == "Linux",
        reason="Skipped on Linux due to broken sfincs binary",
    )
    def test_calculate_rp_floodmaps(
        self, setup_eventset_scenario: tuple[IDatabase, Scenario, EventSet]
    ):
        test_db, scn, event_set = setup_eventset_scenario
        ScenarioRunner(test_db, scenario=scn).run()

        output_path = Path(test_db.scenarios.output_path) / scn.name / "Flooding"

        for rp in test_db.site.fiat.risk.return_periods:
            floodmap_path = output_path / f"RP_{rp:04d}_maps"
            assert (floodmap_path.with_suffix(".nc")).exists()
            assert (floodmap_path.with_suffix(".tif")).exists()
