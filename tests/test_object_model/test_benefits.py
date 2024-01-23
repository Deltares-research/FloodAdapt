from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import tomli

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.benefit import Benefit

test_database = Path().absolute() / "tests" / "test_database"
rng = np.random.default_rng(2021)


def test_benefit_read(test_db):
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


def test_check_scenarios(test_db):
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


def test_run_benefit_analysis(test_db):
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
    aggrs = dbs.get_aggregation_areas()

    # Check that error is returned if not all runs are finished
    if not all(benefit.scenarios["scenario run"]):
        with pytest.raises(RuntimeError):
            # Assert error if not yet run
            benefit.run_cost_benefit()

    # Create dummy results to use for benefit analysis
    damages_dummy = {
        "current_no_measures": 100e6,
        "current_with_strategy": 50e6,
        "future_no_measures": 300e6,
        "future_with_strategy": 180e6,
    }

    for name, row in benefit.scenarios.iterrows():
        # Create output folder
        output_path = (
            test_database
            / "charleston"
            / "output"
            / "Scenarios"
            / row["scenario created"]
        )
        if not output_path.exists():
            output_path.mkdir(parents=True)
        # Create dummy metrics file
        dummy_metrics = pd.DataFrame(
            {
                "Description": "",
                "Show In Metrics Table": "TRUE",
                "Long Name": "",
                "Value": damages_dummy[name],
            },
            index=["ExpectedAnnualDamages"],
        )

        dummy_metrics.to_csv(
            output_path.joinpath(f"Infometrics_{row['scenario created']}.csv")
        )

        # Create dummy metrics for aggregation areas
        for aggr_type in aggrs.keys():
            aggr = aggrs[aggr_type]
            # Generate random distribution of damage per aggregation area
            dmgs = np.random.random(len(aggr))
            dmgs = dmgs / dmgs.sum() * damages_dummy[name]

            dict0 = {
                "Description": ["", ""],
                "Show In Metrics Table": ["TRUE", "TRUE"],
                "Long Name": ["", ""],
            }

            for i, aggr_area in enumerate(aggr["name"]):
                dict0[aggr_area] = [dmgs[i], rng.normal(1, 0.2) * dmgs[i]]

            dummy_metrics_aggr = pd.DataFrame(
                dict0, index=["ExpectedAnnualDamages", "EWEAD"]
            ).T

            dummy_metrics_aggr.to_csv(
                output_path.joinpath(
                    f"Infometrics_{row['scenario created']}_{aggr_type}.csv"
                )
            )

    # Run benefit analysis with dummy data
    benefit.cba()

    # Read results
    results_path = (
        test_database / "charleston" / "output" / "Benefits" / benefit.attrs.name
    )
    with open(results_path.joinpath("results.toml"), mode="rb") as fp:
        results = tomli.load(fp)

    # get results
    tot_benefits = results["benefits"]
    # get time-series
    csv_results = pd.read_csv(results_path.joinpath("time_series.csv"))
    tot_benefits2 = csv_results["benefits_discounted"].sum()

    # assert if time-series and totals are consistent
    assert tot_benefits == tot_benefits2

    # assert if results are equal to the expected values based on the input
    assert pytest.approx(tot_benefits, 2) == 963433925

    # Run benefit analysis with dummy data
    benefit.cba_aggregation()
    # get aggregation
    for aggr_type in aggrs.keys():
        csv_agg_results = pd.read_csv(
            results_path.joinpath(f"benefits_{aggr_type}.csv")
        )
        tot_benefits_agg = csv_agg_results["Benefits"].sum()

        # assert if results are equal to the expected values based on the input
        assert pytest.approx(tot_benefits_agg, 2) == tot_benefits


def test_run_CBA(test_db):
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

    # Create dummy results to use for benefit analysis
    damages_dummy = {
        "current_no_measures": 100e6,
        "current_with_strategy": 50e6,
        "future_no_measures": 300e6,
        "future_with_strategy": 180e6,
    }

    for name, row in benefit.scenarios.iterrows():
        # Create output folder
        output_path = (
            test_database
            / "charleston"
            / "output"
            / "Scenarios"
            / row["scenario created"]
        )
        if not output_path.exists():
            output_path.mkdir(parents=True)
        # Create dummy metrics file
        dummy_metrics = pd.DataFrame(
            {
                "Description": "",
                "Show In Metrics Table": "TRUE",
                "Long Name": "",
                "Value": damages_dummy[name],
            },
            index=["ExpectedAnnualDamages"],
        )
        dummy_metrics.to_csv(
            output_path.joinpath(f"Infometrics_{row['scenario created']}.csv")
        )

    # Run benefit analysis with dummy data
    benefit.cba()

    # Read results
    results_path = (
        test_database / "charleston" / "output" / "Benefits" / benefit.attrs.name
    )
    with open(results_path.joinpath("results.toml"), mode="rb") as fp:
        results = tomli.load(fp)

    # get results
    tot_benefits = results["benefits"]
    tot_costs = results["costs"]
    # get time-series
    csv_results = pd.read_csv(results_path.joinpath("time_series.csv"))
    tot_benefits2 = csv_results["benefits_discounted"].sum()
    tot_costs2 = csv_results["costs_discounted"].sum()

    # assert if time-series and totals are consistent
    assert tot_benefits == tot_benefits2
    assert tot_costs == tot_costs2

    # assert if results are equal to the expected values based on the input
    assert pytest.approx(tot_benefits, 2) == 963433925
    assert pytest.approx(tot_costs, 2) == 201198671
    assert pytest.approx(results["BCR"], 0.01) == 4.79
    assert pytest.approx(results["NPV"], 2) == 762235253
    assert pytest.approx(results["IRR"], 0.01) == 0.394
