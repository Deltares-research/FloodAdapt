from pathlib import Path

import pytest

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import SiteConfig

test_database = Path().absolute() / "tests" / "test_database"


@pytest.mark.skip(
    reason="pydantic not implemented in scenario class yet, still expecting config_io functions"
)
def test_scenario_class():
    test_scenario_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )
    assert test_scenario_toml.is_file()

    test_scenario = Scenario().load("all_projections_extreme12ft_strategy_comb")
    assert isinstance(test_scenario.direct_impacts, DirectImpacts)
    assert isinstance(test_scenario.site_info, SiteConfig)
    assert isinstance(test_scenario.direct_impacts.hazard, Hazard)
    assert isinstance(test_scenario.direct_impacts.impact_strategy, ImpactStrategy)
    assert isinstance(
        test_scenario.direct_impacts.socio_economic_change, SocioEconomicChange
    )
    assert isinstance(test_scenario.direct_impacts.hazard.event, Event)
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy, HazardStrategy
    )
    assert isinstance(
        test_scenario.direct_impacts.hazard.physical_projection, PhysicalProjection
    )

    # Check if all variables are read correctly from the site config file.
    assert test_scenario.site_info.name == "charleston"
    assert test_scenario.site_info.long_name == "Charleston, SC"
    assert test_scenario.site_info.lat == 32.77
    assert test_scenario.site_info.lon == -79.95
    assert test_scenario.site_info.sfincs["cstype"] == "projected"
    assert test_scenario.site_info.gui["tide_harmonic_amplitude"]["value"] == 3.0
    assert test_scenario.site_info.dem["filename"] == "charleston_14m.tif"
    assert test_scenario.site_info.fiat["aggregation_shapefiles"] == "subdivision.shp"
    assert test_scenario.site_info.river["mean_discharge"]["units"] == "cfs"
    assert test_scenario.site_info.obs_station["ID"] == 8665530
    assert test_scenario.site_info.obs_station["mllw"]["value"] == 0.0

    # Check if all variables are read correctly from the scenario file.
    assert (
        test_scenario.direct_impacts.name == "all_projections_extreme12ft_strategy_comb"
    )
    assert (
        test_scenario.direct_impacts.long_name
        == "all_projections - extreme12ft - strategy_comb"
    )
    assert test_scenario.direct_impacts.socio_economic_change
