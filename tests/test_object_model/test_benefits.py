from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.benefit import Benefit

test_database = Path().absolute() / "tests" / "test_database"


def test_benefit_read(cleanup_database):
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


def test_check_scenarios(cleanup_database):
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


@pytest.mark.skip(reason="Takes too long")
def test_run_CBA(cleanup_database):
    dbs = Database(test_database, "charleston")

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

    # Create missing scenarios
    dbs.create_benefit_scenarios(benefit)

    # Check that error is returned if not all runs are finished
    if not all(benefit.scenarios["scenario run"]):
        with pytest.raises(RuntimeError):
            # Assert error if not yet run
            benefit.run_cost_benefit()

    # Runs missing scenarios
    for name, row in benefit.scenarios.iterrows():
        if not row["scenario run"]:
            dbs.run_scenario(row["scenario created"])

    # Check which
    benefit.check_scenarios()

    # Test if all scenarios are ^run^
    assert all(benefit.scenarios["scenario run"])

    benefit.run_cost_benefit()


@pytest.mark.skip(reason="Takes too long")
def test_run_benefit_analysis(cleanup_database):
    dbs = Database(test_database, "charleston")

    benefit_toml = (
        test_database
        / "charleston"
        / "input"
        / "benefits"
        / "benefit_raise_properties_2050_no_costs"
        / "benefit_raise_properties_2050_no_costs.toml"
    )

    assert benefit_toml.is_file()

    benefit = Benefit.load_file(benefit_toml)

    # Create missing scenarios
    dbs.create_benefit_scenarios(benefit)

    # Check that error is returned if not all runs are finished
    if not all(benefit.scenarios["scenario run"]):
        with pytest.raises(RuntimeError):
            # Assert error if not yet run
            benefit.run_cost_benefit()

    # Runs missing scenarios
    for name, row in benefit.scenarios.iterrows():
        if not row["scenario run"]:
            dbs.run_scenario(row["scenario created"])

    # Check which
    benefit.check_scenarios()

    # Test if all scenarios are ^run^
    assert all(benefit.scenarios["scenario run"])

    benefit.run_cost_benefit()
