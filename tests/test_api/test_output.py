import geopandas as gpd
import pandas as pd
import pytest

from flood_adapt.api import output as api_output
from flood_adapt.api import scenarios as api_scenarios


class TestAPI_Output:
    @pytest.fixture(scope="class")
    def scenario(self, test_fa_class):
        scenario_name = "current_extreme12ft_no_measures"
        api_scenarios.run_scenario(scenario_name)
        yield scenario_name

    def test_impact_metrics(self, scenario):
        metrics = api_output.get_infometrics(scenario)
        assert isinstance(metrics, pd.DataFrame)

    def test_impact_footprints(self, scenario):
        footprints = api_output.get_building_footprints(scenario)
        assert isinstance(footprints, gpd.GeoDataFrame)

    def test_impact_get_aggregation(self, scenario):
        aggr_areas = api_output.get_aggregation(scenario)
        assert isinstance(aggr_areas, dict)
