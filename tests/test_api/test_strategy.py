import pytest

from flood_adapt.api import strategies as api_strategies


def test_strategy(test_db):
    strat_with_existing_name = {
        "name": "strategy_comb",
        "description": "strategy_comb",
        "measures": [
            "seawall",
            "raise_property_aggregation_area",
            "raise_property_polygon",
        ],
    }
    # Create a new strategy object with a name that already exists
    strategy = api_strategies.create_strategy(strat_with_existing_name)

    # Save it in the database -> name exists error
    with pytest.raises(ValueError):
        api_strategies.save_strategy(strategy)

    # Delete a strategy which is already used in a scenario
    with pytest.raises(ValueError):
        api_strategies.delete_strategy("strategy_comb")

    # Change to unused name
    strategy.name = "test_strat_1"

    api_strategies.save_strategy(strategy)
    assert api_strategies.get_strategy(strategy.name) == strategy

    api_strategies.delete_strategy(strategy.name)
    with pytest.raises(ValueError):
        api_strategies.get_strategy(strategy.name)
