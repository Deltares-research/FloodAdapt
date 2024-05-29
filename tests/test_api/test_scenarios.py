import pytest

import flood_adapt.api.scenarios as api_scenarios


def test_scenario(test_db):
    test_dict = {
        "name": "current_extreme12ft_no_measures",
        "description": "current_extreme12ft_no_measures",
        "projection": "current",
        "strategy": "no_measures",
    }
    # When user presses add scenario and chooses the measures
    # the dictionary is returned and a Strategy object is created
    with pytest.raises(ValueError):
        # Assert error if the event is not a correct value
        scenario = api_scenarios.create_scenario(test_dict)

    # correct event
    test_dict["event"] = "extreme12ft"
    scenario = api_scenarios.create_scenario(test_dict)

    assert not api_scenarios.save_scenario(scenario)[0]

    # Change name to something new
    test_dict["name"] = "test1"
    scenario = api_scenarios.create_scenario(test_dict)
    api_scenarios.save_scenario(scenario)
    test_db.scenarios.list_objects()

    # If user presses delete scenario the measure is deleted
    api_scenarios.delete_scenario("test1")
    test_db.scenarios.list_objects()


@pytest.mark.skip(reason="Part of test_has_hazard_run")
def test_single_event_run(test_db):
    # Initialize database object
    scenario_name = "current_extreme12ft_no_measures"
    test_db.run_scenario(scenario_name)


@pytest.mark.skip(reason="test takes too much time")
def test_risk_run(test_db):
    # Initialize database object
    scenario_name = "current_test_set_no_measures"
    test_db.run_scenario(scenario_name)
