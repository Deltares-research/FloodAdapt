from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.event.synthetic import Synthetic, TideModel
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site

test_database = Path().absolute() / "tests" / "test_database"


def test_scenario_class():
    scenario_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )
    assert scenario_toml.is_file()

    scenario = Scenario.load_file(scenario_toml)
    scenario.init_object_model()

    assert isinstance(scenario.site_info, Site)
    assert isinstance(scenario.direct_impacts, DirectImpacts)
    assert isinstance(
        scenario.direct_impacts.socio_economic_change, SocioEconomicChange
    )
    assert isinstance(scenario.direct_impacts.impact_strategy, ImpactStrategy)
    assert isinstance(scenario.direct_impacts.hazard, Hazard)
    assert isinstance(scenario.direct_impacts.hazard.hazard_strategy, HazardStrategy)
    assert isinstance(
        scenario.direct_impacts.hazard.physical_projection, PhysicalProjection
    )
    assert isinstance(scenario.direct_impacts.hazard.event, Synthetic)


def test_hazard_load():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()
    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()

    hazard = scenario.direct_impacts.hazard

    assert hazard.event.attrs.timing == "idealized"
    assert isinstance(hazard.event.attrs.tide, TideModel)


def test_hazard_wl():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()

    hazard = scenario.direct_impacts.hazard

    hazard.add_wl_ts()

    assert isinstance(hazard.wl_ts, pd.DataFrame)
    assert len(hazard.wl_ts) > 1
    assert isinstance(hazard.wl_ts.index, pd.DatetimeIndex)


@pytest.mark.skip(reason="wind not implemented yet")
def test_wind_constant():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()

    hazard = scenario.direct_impacts.hazard

    hazard.add_wind_ts()

    assert isinstance(hazard.event_obj.wind_ts, pd.DataFrame)
    assert len(hazard.event_obj.wind_ts) > 1
    assert isinstance(hazard.event_obj.wind_ts.index, pd.DatetimeIndex)
