from pathlib import Path

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


def test_scenario_class():
    scenario_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )
    assert scenario_toml.is_file()

    scenario = Scenario.load_file(scenario_toml)
    scenario.init()
