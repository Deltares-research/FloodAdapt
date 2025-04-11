import pytest

from flood_adapt.config.site import Site
from flood_adapt.objects.projections.projections import (
    PhysicalProjection,
    SocioEconomicChange,
)
from flood_adapt.objects.strategies.hazard_strategy import HazardStrategy
from flood_adapt.objects.strategies.impact_strategy import ImpactStrategy
from flood_adapt.workflows.floodmap import FloodMap
from flood_adapt.workflows.impacts_integrator import Impacts
from flood_adapt.workflows.scenario_runner import Scenario
from tests.test_objects.test_events.test_hurricane import setup_hurricane_event
from tests.test_objects.test_events.test_synthetic import test_event_all_synthetic

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
    assert isinstance(impacts.socio_economic_change, SocioEconomicChange)
    assert isinstance(impacts.impact_strategy, ImpactStrategy)
    assert isinstance(impacts.hazard, FloodMap)
    assert isinstance(impacts.hazard.hazard_strategy, HazardStrategy)
    assert isinstance(impacts.hazard.physical_projection, PhysicalProjection)
