import geopandas as gpd
import pandas as pd
import pytest

import flood_adapt.api.output as api_output
import flood_adapt.api.scenarios as api_scenarios


class TestAPI_Output:
    @pytest.fixture(scope="class")
    def scenario(self, test_db_class):
        scenario_name = "current_extreme12ft_no_measures"
        api_scenarios.run_scenario(scenario_name)
        yield scenario_name

    def test_impact_metrics(self, scenario):
        metrics = api_output.get_infometrics(scenario)
        assert isinstance(metrics, pd.DataFrame)

    def test_impact_footprints(self, scenario):
        footprints = api_output.get_fiat_footprints(scenario)
        assert isinstance(footprints, gpd.GeoDataFrame)

    def test_impact_aggr_damages(self, scenario):
        aggr_areas = api_output.get_aggregation(scenario)
        assert isinstance(aggr_areas, dict)
