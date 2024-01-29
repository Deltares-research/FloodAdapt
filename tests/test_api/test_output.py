import geopandas as gpd
import pandas as pd
import pytest

import flood_adapt.api.output as api_output
import flood_adapt.api.scenarios as api_scenarios


# TODO How to delete the scenario after tests have been run?
@pytest.fixture(scope="session")
def scenario_event(test_db):
    scenario_name = "current_extreme12ft_no_measures"
    api_scenarios.run_scenario(scenario_name, test_db)
    return test_db, scenario_name


def test_impact_metrics(scenario_event):
    test_db, scenario_name = scenario_event
    metrics = api_output.get_infometrics(scenario_name, test_db)
    assert isinstance(metrics, pd.DataFrame)


def test_impact_footprints(scenario_event):
    test_db, scenario_name = scenario_event
    footprints = api_output.get_fiat_footprints(scenario_name, test_db)
    assert isinstance(footprints, gpd.GeoDataFrame)


def test_impact_aggr_areas(scenario_event):
    test_db, scenario_name = scenario_event
    aggr_areas = api_output.get_aggregation(scenario_name, test_db)
    assert isinstance(aggr_areas, dict)
