from pathlib import Path

import pandas as pd

import flood_adapt.api.output as api_output
from flood_adapt.object_model.scenario import Scenario


def test_impact_metrics():
    test_database = Path().absolute() / "tests" / "test_database"
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

    df = api_output.get_impact_metrics(test_scenario)

    assert df is pd.DataFrame
