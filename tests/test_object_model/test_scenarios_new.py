import pytest
from adapter.direct_impacts_integrator import DirectImpacts
from dbs_classes.interface.database import IDatabase
from object_model.direct_impact.impact_strategy import ImpactStrategy
from object_model.hazard.floodmap import FloodMap
from object_model.hazard.hazard_strategy import HazardStrategy
from object_model.interface.projections import (
    PhysicalProjection,
    SocioEconomicChange,
)
from object_model.interface.site import Site
from object_model.scenario import Scenario


@pytest.fixture(autouse=True)
def test_scenarios(test_db):
    test_scns = [
        "current_extreme12ft_no_measures",
        "all_projections_extreme12ft_strategy_comb",
    ]
    yield test_scns


def test_initObjectModel_validInput(test_db, test_scenarios: dict[str, Scenario]):
    test_scenario = test_db.scenarios.get("all_projections_extreme12ft_strategy_comb")

    assert isinstance(test_scenario.site_info, Site)
    assert isinstance(test_scenario.direct_impacts, DirectImpacts)
    assert isinstance(
        test_scenario.direct_impacts.socio_economic_change, SocioEconomicChange
    )
    assert isinstance(test_scenario.direct_impacts.impact_strategy, ImpactStrategy)
    assert isinstance(test_scenario.direct_impacts.hazard, FloodMap)

    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy, HazardStrategy
    )
    assert isinstance(
        test_scenario.direct_impacts.hazard.physical_projection, PhysicalProjection
    )


class Test_scenario_run:
    # @pytest.fixture(scope="class")
    # def test_scenario_run(self, test_db_class: Database):
    #     _proj = test_dict()
    #     _strat = test_attrs()
    #     _event = test_event_all_synthetic()
    #     _scn = {
    #         "name": "test_scn",
    #         "projection": _proj['name'],
    #         "event": _event['name'],
    #         "strategy": _strat['name'],
    #     }
    #     proj = Projection().load_dict(_proj)
    #     strat = Strategy().load_dict(_strat)
    #     event = EventFactory().load_dict(_event)
    #     scn = Scenario().load_dict(_scn)

    #     yield test_db_class, proj, strat, event, scn, _proj, _strat, _event, _scn

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
        to_run.run()

        yield test_db_class, run_name, not_run_name

    def test_run_change_has_run(
        self, test_scenario_before_after_run: tuple[IDatabase, str, str]
    ):
        test_db, run_name, not_run_name = test_scenario_before_after_run

        not_run = test_db.scenarios.get(not_run_name)
        run = test_db.scenarios.get(run_name)

        assert not not_run.direct_impacts.hazard.has_run
        assert run.direct_impacts.hazard.has_run


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
    assert scn.direct_impacts.hazard.has_run