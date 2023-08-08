import shutil
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

    dbs.create_benefit_scenarios(benefit)

    # Test if all scenarios are created
    assert all(benefit.scenarios["scenario created"] != "No")
    # Test that there are scenarios that are not run yet
    assert sum(~benefit.scenarios["scenario run"]) > 0

    with pytest.raises(RuntimeError):
        # Assert error if not yet run
        benefit.run_cost_benefit()

    # Simulate FIAT run by creating the results folder for each run and adding a csv with a total EAD
    EADs = pd.Series(
        {
            "current_no_measures": 10000000,
            "current_with_strategy": 3000000,
            "future_no_measures": 16000000,
            "future_with_strategy": 5000000,
        }
    )

    results_path = test_database.joinpath("charleston", "output", "results")
    for index, scenario in benefit.scenarios.iterrows():
        res_scn_path = results_path.joinpath(scenario["scenario created"]).joinpath(
            "fiat_model"
        )
        res_scn_path.mkdir(parents=True)

        df = pd.DataFrame({"EAD": EADs[index]}, index=[0])
        df.to_csv(res_scn_path.joinpath("metrics.csv"), index=False)

    benefit.check_scenarios()
    # Test if all scenarios are ^run^
    assert all(benefit.scenarios["scenario run"])

    benefit.run_cost_benefit()

    # Delete created files
    scenarios_path = test_database.joinpath("charleston", "input", "scenarios")
    path1 = scenarios_path.joinpath("all_projections_test_set_elevate_comb_correct")
    path2 = scenarios_path.joinpath("all_projections_test_set_no_measures")
    path3 = scenarios_path.joinpath("current_test_set_elevate_comb_correct")
    # Delete scenarios created
    shutil.rmtree(path1)
    shutil.rmtree(path2)
    shutil.rmtree(path3)

    for index, scenario in benefit.scenarios.iterrows():
        res_scn_path = results_path.joinpath(scenario["scenario created"])
        shutil.rmtree(res_scn_path)


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

    dbs.create_benefit_scenarios(benefit)

    # Test if all scenarios are created
    assert all(benefit.scenarios["scenario created"] != "No")
    # Test that there are scenarios that are not run yet
    assert sum(~benefit.scenarios["scenario run"]) > 0

    with pytest.raises(RuntimeError):
        # Assert error if not yet run
        benefit.run_cost_benefit()

    # Simulate FIAT run by creating the results folder for each run and adding a csv with a total EAD
    EADs = pd.Series(
        {
            "current_no_measures": 10000000,
            "current_with_strategy": 3000000,
            "future_no_measures": 16000000,
            "future_with_strategy": 5000000,
        }
    )

    results_path = test_database.joinpath("charleston", "output", "results")
    for index, scenario in benefit.scenarios.iterrows():
        res_scn_path = results_path.joinpath(scenario["scenario created"]).joinpath(
            "fiat_model"
        )
        res_scn_path.mkdir(parents=True)

        df = pd.DataFrame({"EAD": EADs[index]}, index=[0])
        df.to_csv(res_scn_path.joinpath("metrics.csv"), index=False)

    benefit.check_scenarios()
    # Test if all scenarios are ^run^
    assert all(benefit.scenarios["scenario run"])

    benefit.run_cost_benefit()

    # Delete created files
    scenarios_path = test_database.joinpath("charleston", "input", "scenarios")
    path1 = scenarios_path.joinpath("all_projections_test_set_elevate_comb_correct")
    path2 = scenarios_path.joinpath("all_projections_test_set_no_measures")
    path3 = scenarios_path.joinpath("current_test_set_elevate_comb_correct")
    # Delete scenarios created
    shutil.rmtree(path1)
    shutil.rmtree(path2)
    shutil.rmtree(path3)

    for index, scenario in benefit.scenarios.iterrows():
        res_scn_path = results_path.joinpath(scenario["scenario created"])
        shutil.rmtree(res_scn_path)
