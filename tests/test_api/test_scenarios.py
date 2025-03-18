import shutil
from pathlib import Path

import pytest

from flood_adapt.api import scenarios as api_scenarios
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.utils import finished_file_exists
from tests.test_adapter.test_sfincs_adapter import mock_meteohandler_read
from tests.test_object_model.test_events.test_eventset import (
    test_eventset,
    test_sub_event,
)
from tests.test_object_model.test_events.test_historical import (
    setup_nearshore_event,
    setup_offshore_meteo_event,
    setup_offshore_scenario,
)
from tests.test_object_model.test_events.test_hurricane import setup_hurricane_event
from tests.test_object_model.test_events.test_synthetic import test_event_all_synthetic

# To stop ruff from deleting these 'unused' imports
__all__ = [
    "test_eventset",
    "test_sub_event",
    "test_event_all_synthetic",
    "setup_nearshore_event",
    "setup_offshore_meteo_event",
    "setup_offshore_scenario",
    "setup_hurricane_event",
    "mock_meteohandler_read",
]


@pytest.fixture()
def setup_nearshore_scenario(test_db, setup_nearshore_event):
    test_db.events.save(setup_nearshore_event)

    scn = Scenario(
        ScenarioModel(
            name="gauged_nearshore",
            description="current_extreme12ft_no_measures",
            event=setup_nearshore_event.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )
    return scn


@pytest.fixture()
def setup_offshore_meteo_scenario(
    test_db,
    setup_offshore_meteo_event,
    mock_meteohandler_read,
):
    test_db.events.save(setup_offshore_meteo_event)

    scn = Scenario(
        ScenarioModel(
            name="offshore_meteo",
            event=setup_offshore_meteo_event.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )

    return scn


@pytest.fixture()
def setup_hurricane_scenario(
    test_db: IDatabase,
    setup_hurricane_event: tuple[HurricaneEvent, Path],
    mock_meteohandler_read,
) -> tuple[Scenario, HurricaneEvent]:
    event, cyc_file = setup_hurricane_event
    scn = Scenario(
        ScenarioModel(
            name="hurricane",
            event=event.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )
    test_db.events.save(event)
    shutil.copy2(cyc_file, test_db.events.input_path / event.attrs.name / cyc_file.name)
    test_db.scenarios.save(scn)
    return scn, event


@pytest.fixture()
def setup_synthetic_scenario(test_db, test_event_all_synthetic):
    test_db.events.save(test_event_all_synthetic)

    scn = Scenario(
        ScenarioModel(
            name="synthetic",
            event=test_event_all_synthetic.attrs.name,
            projection="current",
            strategy="no_measures",
        )
    )
    return scn


@pytest.fixture()
def setup_eventset_scenario(
    test_db: IDatabase,
    test_eventset,
    dummy_projection,
    dummy_strategy,
):
    test_db.projections.save(dummy_projection)
    test_db.strategies.save(dummy_strategy)

    test_db.events.save(test_eventset)

    scn = Scenario(
        ScenarioModel(
            name="test_scenario",
            event=test_eventset.attrs.name,
            projection=dummy_projection.attrs.name,
            strategy=dummy_strategy.attrs.name,
        )
    )
    return test_db, scn, test_eventset


@pytest.mark.slow
def test_run_offshore_scenario(test_db, setup_offshore_meteo_scenario):
    api_scenarios.save_scenario(setup_offshore_meteo_scenario)
    api_scenarios.run_scenario(setup_offshore_meteo_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.output_path / setup_offshore_meteo_scenario.attrs.name
    )


def test_run_nearshore_scenario(test_db, setup_nearshore_scenario):
    api_scenarios.save_scenario(setup_nearshore_scenario)
    api_scenarios.run_scenario(setup_nearshore_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.output_path / setup_nearshore_scenario.attrs.name
    )


def test_run_synthetic_scenario(test_db, setup_synthetic_scenario):
    api_scenarios.save_scenario(setup_synthetic_scenario)
    api_scenarios.run_scenario(setup_synthetic_scenario.attrs.name)

    assert finished_file_exists(
        test_db.scenarios.output_path / setup_synthetic_scenario.attrs.name
    )


@pytest.mark.slow
def test_run_hurricane_scenario(test_db, setup_hurricane_scenario):
    scn, event = setup_hurricane_scenario
    api_scenarios.save_scenario(scn)
    api_scenarios.run_scenario(scn.attrs.name)

    assert finished_file_exists(test_db.scenarios.output_path / scn.attrs.name)


@pytest.mark.slow
def test_run_eventset_scenario(setup_eventset_scenario):
    test_db, scn, event_set = setup_eventset_scenario
    api_scenarios.save_scenario(scn)
    api_scenarios.run_scenario(scn.attrs.name)

    assert finished_file_exists(test_db.scenarios.output_path / scn.attrs.name)


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
