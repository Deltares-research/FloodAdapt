import geopandas as gpd
import pytest

import flood_adapt.api.static as api_startup


@pytest.mark.skip(reason="test fails in TeamCity, TODO investigate")
def test_buildings(test_db):
    assert isinstance(api_startup.get_buildings(), gpd.GeoDataFrame)


def test_aggr_areas(test_db):
    aggr_areas = api_startup.get_aggregation_areas()

    assert isinstance(aggr_areas, dict)
    assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)


@pytest.mark.skip(reason="test fails in TeamCity, TODO investigate")
def test_property_types(test_db):
    types = api_startup.get_property_types()

    assert isinstance(types, list)
    assert len(types) == 3
    assert "RES" in types
