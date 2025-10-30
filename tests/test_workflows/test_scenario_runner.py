import platform

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects import HurricaneEvent, Scenario
from flood_adapt.workflows.scenario_runner import ScenarioRunner
from tests.test_objects.test_events.conftest import setup_hurricane_event

__all__ = ["setup_hurricane_event"]


@pytest.mark.skipif(
    platform.system() == "Linux",
    reason="Skipped on Linux due to broken sfincs binary",
)
class Test_scenario_run:
    @pytest.fixture(scope="class")
    def test_scenario_before_after_run(self, test_db_class: IDatabase):
        run_name = "all_projections_extreme12ft_strategy_comb"
        not_run_name = f"{run_name}_NOT_RUN"

        test_db_class.scenarios.copy(
            old_name=run_name,
            new_name=not_run_name,
            new_description="temp_description",
        )

        to_run = test_db_class.scenarios.get(run_name)
        ScenarioRunner(test_db_class, scenario=to_run).run()

        yield test_db_class, run_name, not_run_name

    def test_run_change_has_run(
        self, test_scenario_before_after_run: tuple[IDatabase, str, str]
    ):
        test_db, run_name, not_run_name = test_scenario_before_after_run

        not_run = test_db.scenarios.get(not_run_name)
        run = test_db.scenarios.get(run_name)

        assert not ScenarioRunner(database=test_db, scenario=not_run).has_run_check()
        assert ScenarioRunner(database=test_db, scenario=run).has_run_check()

    @pytest.fixture()
    def setup_hurricane_scenario(
        self,
        test_db: IDatabase,
        setup_hurricane_event: HurricaneEvent,
    ) -> tuple[IDatabase, Scenario, HurricaneEvent]:
        event = setup_hurricane_event
        scn = Scenario(
            name="hurricane",
            event=event.name,
            projection="current",
            strategy="no_measures",
        )
        test_db.events.save(event)
        test_db.scenarios.save(scn)
        return test_db, scn, event

    def test_run_hurricane_scenario(
        self, setup_hurricane_scenario: tuple[IDatabase, Scenario, HurricaneEvent]
    ):
        # Arrange
        test_db, scn, event = setup_hurricane_scenario

        # Act
        ScenarioRunner(test_db, scenario=scn).run()

        # Assert
        assert finished_file_exists(test_db.scenarios.output_path / scn.name)


@pytest.mark.skipif(
    platform.system() == "Linux", reason="Skipped on Linux due to broken sfincs binary"
)
@pytest.mark.parametrize(
    "scn_name",
    [
        "all_projections_extreme12ft_strategy_comb",
        "current_extreme12ft_no_measures",
        "current_extreme12ft_raise_datum",
        "current_extreme12ft_rivershape_windconst_no_measures",
        "current_extreme12ft_strategy_impact_comb",
    ],
)
def test_run_on_all_scn(test_db, scn_name):
    scn = test_db.scenarios.get(scn_name)
    runner = ScenarioRunner(test_db, scenario=scn)
    runner.run()
    assert runner.has_run_check()
