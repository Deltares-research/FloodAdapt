from pathlib import Path

import geopandas as gpd

import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_buildings():
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    assert isinstance(database.get_buildings(), gpd.GeoDataFrame)


def test_aggr_areas():
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)
    aggr_areas = database.get_aggregation_areas()
    assert isinstance(aggr_areas, dict)
    assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)
