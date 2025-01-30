import geopandas as gpd

from flood_adapt.api import static as api_static


def test_buildings(test_db):
    assert isinstance(api_static.get_buildings(), gpd.GeoDataFrame)


def test_aggr_areas(test_db):
    aggr_areas = api_static.get_aggregation_areas()

    assert isinstance(aggr_areas, dict)
    assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)


def test_property_types(test_db):
    types = api_static.get_property_types()
    expected_types = ["RES", "COM", "road", "all"]

    assert isinstance(types, list)
    assert len(types) == 4
    assert all(t in types for t in expected_types)
