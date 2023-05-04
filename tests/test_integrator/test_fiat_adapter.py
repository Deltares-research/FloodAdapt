from pathlib import Path

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


def test_fiat_adapter_no_measures():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.init_object_model()
    # TODO: Hazard class should check if the hazard simulation has already been run when initialized
    test_scenario.direct_impacts.hazard.has_run = True  # manually change this for now
    test_scenario.direct_impacts.run_fiat()


def test_fiat_adapter_measures():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.init_object_model()
    # TODO: Hazard class should check if the hazard simulation has already been run when initialized
    test_scenario.direct_impacts.hazard.has_run = True  # manually change this for now
    test_scenario.direct_impacts.run_fiat()
