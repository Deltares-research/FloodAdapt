from pathlib import Path

import pytest

import flood_adapt.api.scenarios as api_scenarios
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
test_site_name = "charleston"


def test_scenario(cleanup_database):
    test_dict = {
        "name": "current_extreme12ft_no_measures",
        "description": "current_extreme12ft_no_measures",
        "projection": "current",
        "strategy": "no_measures",
    }
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)

    # When user presses add scenario and chooses the measures
    # the dictionary is returned and a Strategy object is created
    with pytest.raises(ValueError):
        # Assert error if the event is not a correct value
        scenario = api_scenarios.create_scenario(test_dict, database)

    # correct event
    test_dict["event"] = "extreme12ft"
    scenario = api_scenarios.create_scenario(test_dict, database)

    assert not api_scenarios.save_scenario(scenario, database)[0]

    # Change name to something new
    test_dict["name"] = "test1"
    scenario = api_scenarios.create_scenario(test_dict, database)
    api_scenarios.save_scenario(scenario, database)
    database.get_scenarios()

    # If user presses delete scenario the measure is deleted
    api_scenarios.delete_scenario("test1", database)
    database.get_scenarios()


@pytest.mark.skip(reason="Part of test_has_hazard_run")
def test_single_event_run(cleanup_database):
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)
    scenario_name = "current_extreme12ft_no_measures"
    database.run_scenario(scenario_name)


@pytest.mark.skip(reason="test takes too much time")
def test_risk_run(cleanup_database):
    # Initialize database object
    database = api_startup.read_database(test_database_path, test_site_name)
    scenario_name = "current_test_set_no_measures"
    database.run_scenario(scenario_name)
