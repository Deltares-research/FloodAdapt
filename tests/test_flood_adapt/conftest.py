import pytest

from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.objects.events.hurricane import HurricaneEvent
from flood_adapt.objects.scenarios.scenarios import Scenario


@pytest.fixture()
def setup_nearshore_scenario(test_fa: FloodAdapt, setup_nearshore_event):
    test_fa.save_event(setup_nearshore_event)

    scn = Scenario(
        name="gauged_nearshore",
        description="current_extreme12ft_no_measures",
        event=setup_nearshore_event.name,
        projection="current",
        strategy="no_measures",
    )
    return scn


@pytest.fixture()
def setup_offshore_meteo_scenario(
    test_fa: FloodAdapt,
    setup_offshore_meteo_event,
    mock_meteohandler_read,
):
    test_fa.save_event(setup_offshore_meteo_event)

    scn = Scenario(
        name="offshore_meteo",
        event=setup_offshore_meteo_event.name,
        projection="current",
        strategy="no_measures",
    )

    return scn


@pytest.fixture()
def setup_hurricane_scenario(
    test_fa: FloodAdapt,
    setup_hurricane_event: HurricaneEvent,
    mock_meteohandler_read,
) -> tuple[Scenario, HurricaneEvent]:
    event = setup_hurricane_event
    scn = Scenario(
        name="hurricane",
        event=event.name,
        projection="current",
        strategy="no_measures",
    )
    test_fa.save_event(event)

    return scn, event


@pytest.fixture()
def setup_synthetic_scenario(test_fa: FloodAdapt, test_event_all_synthetic):
    test_fa.save_event(test_event_all_synthetic)

    scn = Scenario(
        name="synthetic",
        event=test_event_all_synthetic.name,
        projection="current",
        strategy="no_measures",
    )
    return scn


@pytest.fixture()
def setup_eventset_scenario(
    test_fa: FloodAdapt, dummy_projection, dummy_strategy, test_eventset
):
    test_fa.save_projection(dummy_projection)
    for measure in dummy_strategy.get_measures():
        test_fa.save_measure(measure)
    test_fa.save_strategy(dummy_strategy)
    test_fa.save_event(test_eventset)

    scn = Scenario(
        name="test_risk_scenario_with_hurricanes",
        event=test_eventset.name,
        projection=dummy_projection.name,
        strategy=dummy_strategy.name,
    )
    return test_fa, scn, test_eventset
