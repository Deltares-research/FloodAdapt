import shutil

import pytest

import flood_adapt.api.strategies as api_strategies


def test_strategy(test_db):
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
    # When user presses add strategy and chooses the measures
    # the dictionary is returned and a Strategy object is created
    with pytest.raises(ValueError):
        # Assert error if there are overlapping measures
        strategy = api_strategies.create_strategy(test_dict, test_db)

    # correct measures
    test_dict["measures"] = [
        "seawall",
        "raise_property_aggregation_area",
        "raise_property_polygon",
    ]
    strategy = api_strategies.create_strategy(test_dict, test_db)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_strategies.save_strategy(strategy, test_db)

    # Change name to something new
    test_dict["name"] = "test_strat_1"
    # delete an old one if it already exists
    if test_db.input_path.joinpath("strategies", test_dict["name"]).is_dir():
        shutil.rmtree(test_db.input_path.joinpath("strategies", test_dict["name"]))

    # create new one
    strategy = api_strategies.create_strategy(test_dict, test_db)
    # If the name is not used before the measure is save in the database
    api_strategies.save_strategy(strategy, test_db)
    test_db.strategies.list_objects()

    # Try to delete a measure which is already used in a scenario
    # with pytest.raises(ValueError):
    #     api_strategies.delete_measure("", database)

    # If user presses delete strategy the measure is deleted
    api_strategies.delete_strategy("test_strat_1", test_db)
    test_db.strategies.list_objects()
