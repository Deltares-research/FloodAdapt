from pathlib import Path

import pandas as pd

from flood_adapt.object_model.benefit import Benefit

test_database = Path().absolute() / "tests" / "test_database"


def test_benefit_read():
    benefit_toml = (
        test_database
        / "charleston"
        / "input"
        / "benefits"
        / "benefit_raise_properties_2050"
        / "benefit_raise_properties_2050.toml"
    )

    assert benefit_toml.is_file()
    benefit = Benefit.load_file(benefit_toml)
    assert isinstance(benefit, Benefit)


def test_check_scenarios():
    benefit_toml = (
        test_database
        / "charleston"
        / "input"
        / "benefits"
        / "benefit_raise_properties_2050"
        / "benefit_raise_properties_2050.toml"
    )

    assert benefit_toml.is_file()

    benefit = Benefit.load_file(benefit_toml)
    df_check = benefit.check_scenarios()
    assert isinstance(df_check, pd.DataFrame)
