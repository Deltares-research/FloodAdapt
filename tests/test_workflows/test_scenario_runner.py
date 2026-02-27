from pathlib import Path
from textwrap import dedent

import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.events.hurricane import HurricaneEvent
from flood_adapt.workflows.scenario_runner import Scenario, ScenarioRunner
from tests.conftest import CAN_EXECUTE_SCENARIOS
from tests.test_objects.test_events.test_hurricane import setup_hurricane_event

# mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

__all__ = ["setup_hurricane_event"]


@pytest.mark.skipif(
    not CAN_EXECUTE_SCENARIOS,
    reason="Only run when we can execute scenarios. Requires either a working sfincs binary, or a working docker setup",
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
        test_db.events.add(event)
        test_db.scenarios.add(scn)
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
    not CAN_EXECUTE_SCENARIOS,
    reason="Only run when we can execute scenarios. Requires either a working sfincs binary, or a working docker setup",
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


@pytest.fixture()
def test_db_qt(test_db: IDatabase) -> IDatabase:
    test_db.read_site(site_name="site_quadtree")
    return test_db


@pytest.mark.skipif(
    not CAN_EXECUTE_SCENARIOS,
    reason="Only run when we can execute scenarios. Requires either a working sfincs binary, or a working docker setup",
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
def test_run_on_all_scn_quadtree(test_db_qt: IDatabase, scn_name: str):
    scn = test_db_qt.scenarios.get(scn_name)
    runner = ScenarioRunner(test_db_qt, scenario=scn)
    runner.run()
    assert runner.has_run_check()


@pytest.fixture
def test_db_with_postprocessing_hooks(
    test_db: IDatabase,
) -> tuple[IDatabase, list[str]]:
    HOOK_CODE = dedent(
        """\
        def postprocess(database, scenario, results_path):
            path = results_path / 'postprocess_{i}_ran.txt'
            path.write_text(f'postprocessed {{scenario.name}}')
        """  # use double `{{}}` to allow the .format() to work without trying to format the inner {scenario.name}
    )
    from flood_adapt.config.database import PostProcessingHook

    hooks = []
    for i in range(1, 3):
        rel_in_db = Path("postprocessing", f"postprocess_hook_{i}.py")
        abs_in_db = test_db.static_path / rel_in_db
        abs_in_db.parent.mkdir(parents=True, exist_ok=True)
        abs_in_db.write_text(HOOK_CODE.format(i=i))
        hooks.append(
            PostProcessingHook(name=f"postprocess_hook_{i}", path=rel_in_db.as_posix())
        )

    test_db.config.post_processing_hooks = hooks
    return test_db, [f"postprocess_{i}_ran.txt" for i in range(1, 3)]


def test_postprocessing_hook_execution(
    test_db_with_postprocessing_hooks: tuple[IDatabase, list[str]],
):
    test_db, created_files = test_db_with_postprocessing_hooks
    # Run the post-processing hook directly
    scn = Scenario(
        name="test_scenario",
        event="event",
        projection="current",
        strategy="no_measures",
    )
    runner = ScenarioRunner(test_db, scenario=scn)
    runner.results_path.mkdir(parents=True, exist_ok=True)  # Ensure results path exists
    runner._run_postprocessing_hooks()

    # Check that the post-processing hook created the expected file
    assert all((runner.results_path / rel_path).exists() for rel_path in created_files)

    # Check that scenario.name was written correctly
    for marker_filename in created_files:
        content = (runner.results_path / marker_filename).read_text()
        assert f"postprocessed {scn.name}" in content
