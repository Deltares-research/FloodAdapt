import pytest

from flood_adapt.adapter.impacts_integrator import Impacts
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.projections import (
    PhysicalProjectionModel,
    SocioEconomicChangeModel,
)
from flood_adapt.object_model.scenario_runner import Scenario, ScenarioRunner
from flood_adapt.object_model.utils import finished_file_exists
from tests.test_object_model.test_events.test_hurricane import setup_hurricane_event
from tests.test_object_model.test_events.test_synthetic import test_event_all_synthetic

# To stop ruff from deleting these 'unused' imports
__all__ = [
    "test_event_all_synthetic",
    "setup_hurricane_event",
]


@pytest.fixture(autouse=True)
def test_scenarios(test_db):
    test_scns = [
        "current_extreme12ft_no_measures",
        "all_projections_extreme12ft_strategy_comb",
    ]
    yield test_scns


def test_init_valid_input(test_db, test_scenarios: dict[str, Scenario]):
    test_scenario = test_db.scenarios.get("all_projections_extreme12ft_strategy_comb")
    impacts = Impacts(test_scenario)
    assert isinstance(impacts, Impacts)
    assert isinstance(impacts.site_info, Site)
    assert isinstance(impacts.socio_economic_change, SocioEconomicChangeModel)
    assert isinstance(impacts.impact_strategy, ImpactStrategy)
    assert isinstance(impacts.hazard, FloodMap)
    assert isinstance(impacts.hazard.hazard_strategy, HazardStrategy)
    assert isinstance(impacts.hazard.physical_projection, PhysicalProjectionModel)


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
        ScenarioRunner(test_db_class, scenario=to_run).run(to_run)

        yield test_db_class, run_name, not_run_name

    def test_run_change_has_run(
        self, test_scenario_before_after_run: tuple[IDatabase, str, str]
    ):
        test_db, run_name, not_run_name = test_scenario_before_after_run

        not_run = test_db.scenarios.get(not_run_name)
        run = test_db.scenarios.get(run_name)

        assert not Impacts(not_run).hazard.has_run
        assert Impacts(run).hazard.has_run

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
        runner = ScenarioRunner(test_db, scenario=scn)

        # Act
        runner.run(scn)

        # Assert
        assert finished_file_exists(test_db.scenarios.output_path / scn.name)


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
    runner.run(scn)
    assert Impacts(scn).hazard.has_run
