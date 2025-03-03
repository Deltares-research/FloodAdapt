import shutil
from pathlib import Path

import pytest

from flood_adapt.adapter.impacts_integrator import Impacts
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.projections import (
    PhysicalProjection,
    SocioEconomicChange,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.scenario import Scenario
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

    assert isinstance(test_scenario.site_info, Site)
    assert isinstance(test_scenario.impacts, Impacts)
    assert isinstance(test_scenario.impacts.socio_economic_change, SocioEconomicChange)
    assert isinstance(test_scenario.impacts.impact_strategy, ImpactStrategy)
    assert isinstance(test_scenario.impacts.flood_map, FloodMap)

    assert isinstance(test_scenario.impacts.hazard.hazard_strategy, HazardStrategy)
    assert isinstance(
        test_scenario.impacts.hazard.physical_projection, PhysicalProjection
    )


class Test_scenario_run:
    @pytest.fixture(scope="class")
    def test_scenario_before_after_run(self, test_fa_class: FloodAdapt):
        run_name = "all_projections_extreme12ft_strategy_comb"
        not_run_name = f"{run_name}_NOT_RUN"

        test_fa_class.database.scenarios.copy(
            old_name=run_name,
            new_name=not_run_name,
            new_description="temp_description",
        )
        test_fa_class.run_scenario(run_name)

        yield test_fa_class, run_name, not_run_name

    def test_run_change_has_run(
        self, test_scenario_before_after_run: tuple[IDatabase, str, str]
    ):
        test_db, run_name, not_run_name = test_scenario_before_after_run

        not_run = test_db.scenarios.get(not_run_name)
        run = test_db.scenarios.get(run_name)

        assert not not_run.impacts.hazard.has_run
        assert run.impacts.hazard.has_run

    @pytest.fixture()
    def setup_hurricane_scenario(
        self,
        test_db: IDatabase,
        setup_hurricane_event: tuple[HurricaneEvent, Path],
    ) -> tuple[IDatabase, Scenario, HurricaneEvent]:
        event, cyc_file = setup_hurricane_event
        scn = Scenario(
            ScenarioModel(
                name="hurricane",
                event=event.attrs.name,
                projection="current",
                strategy="no_measures",
            )
        )
        test_db.events.save(event)
        shutil.copy2(
            cyc_file, test_db.events.input_path / event.attrs.name / cyc_file.name
        )
        test_db.scenarios.save(scn)
        return test_db, scn, event

    def test_run_hurricane_scenario(
        self, setup_hurricane_scenario: tuple[IDatabase, Scenario, HurricaneEvent]
    ):
        # Arrange
        test_db, scn, event = setup_hurricane_scenario

        # Act
        scn.run()

        # Assert
        assert finished_file_exists(test_db.scenarios.output_path / scn.attrs.name)


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
    scn.run()
    assert scn.impacts.hazard.has_run
