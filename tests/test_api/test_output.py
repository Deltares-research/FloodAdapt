from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest

import flood_adapt.api.output as api_output
import flood_adapt.api.scenarios as api_scenarios
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"
database_path = str(test_database_path)  # .joinpath(test_site_name))
test_database = api_startup.read_database(database_path, test_site_name)

# TODO How to delete the scenario after tests have been run?
@pytest.fixture(scope="session")
def scenario_event():
    name = "current_extreme12ft_no_measures"
    api_scenarios.run_scenario(name, test_database)
    return name


def test_impact_metrics(scenario_event):
    metrics = api_output.get_infometrics(scenario_event, test_database)
    assert isinstance(metrics, pd.DataFrame)


def test_impact_footprints(scenario_event):
    footprints = api_output.get_fiat_footprints(scenario_event, test_database)
    assert isinstance(footprints, gpd.GeoDataFrame)


def test_impact_aggr_areas(scenario_event):
    aggr_areas = api_output.get_aggregation(scenario_event, test_database)
    assert isinstance(aggr_areas, dict)
