import pytest

import flood_adapt.api.scenarios as api_scenarios
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.utils import finished_file_exists


@pytest.fixture()
def setup_nearshore_scenario(test_db, setup_nearshore_event):
    test_db.events.save(setup_nearshore_event)

    test_dict = {
        "name": "gauged_nearshore",
        "description": "current_extreme12ft_no_measures",
        "event": setup_nearshore_event.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    return Scenario.load_dict(test_dict)


@pytest.fixture()
def setup_offshore_meteo_scenario(test_db, setup_offshore_meteo_event):
    test_db.events.save(setup_offshore_meteo_event)

    test_dict = {
        "name": "offshore_meteo",
        "description": "current_extreme12ft_no_measures",
        "event": setup_offshore_meteo_event.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    return Scenario.load_dict(test_dict)


@pytest.fixture()
def setup_synthetic_scenario(test_db, test_event_all_synthetic):
    test_db.events.save(test_event_all_synthetic)
    test_dict = {
        "name": "synthetic",
        "description": "current_extreme12ft_no_measures",
        "event": test_event_all_synthetic.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    return Scenario.load_dict(test_dict)


@pytest.fixture()
def setup_eventset_scenario(test_db, test_eventset):
    test_db.events.save(test_eventset)
    test_dict = {
        "name": "eventset",
        "description": "current_extreme12ft_no_measures",
        "event": test_eventset.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    return Scenario.load_dict(test_dict)


def test_run_offshore_scenario(test_db, setup_offshore_meteo_scenario):
    api_scenarios.save_scenario(setup_offshore_meteo_scenario)
    api_scenarios.run_scenario(setup_offshore_meteo_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.get_database_path(get_input_path=False)
        / setup_offshore_meteo_scenario.attrs.name
    )


def test_run_nearshore_scenario(test_db, setup_nearshore_scenario):
    api_scenarios.save_scenario(setup_nearshore_scenario)
    api_scenarios.run_scenario(setup_nearshore_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.get_database_path(get_input_path=False)
        / setup_nearshore_scenario.attrs.name
    )


def test_run_synthetic_scenario(test_db, setup_synthetic_scenario):
    api_scenarios.save_scenario(setup_synthetic_scenario)
    api_scenarios.run_scenario(setup_synthetic_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.get_database_path(get_input_path=False)
        / setup_synthetic_scenario.attrs.name
    )


def test_run_eventset_scenario(test_db, setup_eventset_scenario):
    api_scenarios.save_scenario(setup_eventset_scenario)
    api_scenarios.run_scenario(setup_eventset_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.get_database_path(get_input_path=False)
        / setup_eventset_scenario.attrs.name
    )


def test_create_save_scenario(test_db, setup_offshore_meteo_event):
    test_db.events.save(setup_offshore_meteo_event)

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
    test_dict["event"] = setup_offshore_meteo_event.attrs.name
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
