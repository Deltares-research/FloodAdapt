import geopandas as gpd

import flood_adapt.api.startup as api_startup


def test_buildings(test_db):
    assert isinstance(api_startup.get_buildings(test_db), gpd.GeoDataFrame)


def test_aggr_areas(test_db):
    aggr_areas = api_startup.get_aggregation_areas(test_db)

    assert isinstance(aggr_areas, dict)
    assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)


def test_property_types(test_db):
    types = api_startup.get_property_types(test_db)

    assert isinstance(types, list)
    assert len(types) == 3
    assert "RES" in types
