import shutil
from pathlib import Path

import pytest

import flood_adapt.api.startup as api_startup
import flood_adapt.api.strategies as api_strategies

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_strategy():
    test_dict = {
        "name": "strategy_comb",
        "description": "strategy_comb",
        "measures": [
            "seawall",
            "raise_property_aggregation_area",
            "raise_property_polygon",
            "raise_property_all_properties",
        ],
    }
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    # When user presses add strategy and chooses the measures
    # the dictionary is returned and a Strategy object is created
    with pytest.raises(ValueError):
        # Assert error if there are overlapping measures
        strategy = api_strategies.create_strategy(test_dict, database)

    # correct measures
    test_dict["measures"] = [
        "seawall",
        "raise_property_aggregation_area",
        "raise_property_polygon",
    ]
    strategy = api_strategies.create_strategy(test_dict, database)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_strategies.save_strategy(strategy, database)

    # Change name to something new
    test_dict["name"] = "test1"
    # delete an old one if it already exists
    if database.input_path.joinpath("strategies", test_dict["name"]).is_dir():
        shutil.rmtree(database.input_path.joinpath("strategies", test_dict["name"]))

    # create new one
    strategy = api_strategies.create_strategy(test_dict, database)
    # If the name is not used before the measure is save in the database
    api_strategies.save_strategy(strategy, database)
    database.get_strategies()

    # Try to delete a measure which is already used in a scenario
    # with pytest.raises(ValueError):
    #     api_strategies.delete_measure("", database)

    # If user presses delete strategy the measure is deleted
    api_strategies.delete_strategy("test1", database)
    database.get_strategies()
