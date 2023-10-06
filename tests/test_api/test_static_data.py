from pathlib import Path

import geopandas as gpd

import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_buildings(cleanup_database):
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    assert isinstance(api_startup.get_buildings(database), gpd.GeoDataFrame)


def test_aggr_areas(cleanup_database):
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)
    aggr_areas = api_startup.get_aggregation_areas(database)
    assert isinstance(aggr_areas, dict)
    assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)


def test_property_types(cleanup_database):
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)
    types = api_startup.get_property_types(database)
    assert isinstance(types, list)
    assert len(types) == 3
    assert "RES" in types
