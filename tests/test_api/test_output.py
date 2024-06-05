import geopandas as gpd
import pandas as pd
import pytest

import flood_adapt.api.output as api_output
import flood_adapt.api.scenarios as api_scenarios


@pytest.fixture(scope="session")
def scenario_event(test_db_session):
    scenario_name = "current_extreme12ft_no_measures"
    api_scenarios.run_scenario(scenario_name)
    return test_db_session, scenario_name


def test_impact_metrics(scenario_event):
    _, scenario_name = scenario_event
    metrics = api_output.get_infometrics(scenario_name)
    assert isinstance(metrics, pd.DataFrame)


def test_impact_footprints(scenario_event):
    test_db_session, scenario_name = scenario_event
    footprints = api_output.get_impact_building_footprints(
        scenario_name, test_db_session
    )
    assert isinstance(footprints, gpd.GeoDataFrame)


def test_impact_aggr_areas(scenario_event):
    _, scenario_name = scenario_event
    aggr_areas = api_output.get_aggregation(scenario_name)
    assert isinstance(aggr_areas, dict)
