from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import flood_adapt.api.benefits as api_benefits
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
site_name = "charleston"
rng = np.random.default_rng(2021)


def test_benefit(test_db):
    # Initialize database object
    database = api_startup.read_database(test_database_path, site_name)

    # Inputs for benefit calculation
    # Name given already exists to do test for error capture
    benefit_dict = {
        "name": "benefit_raise_properties_2050",
        "description": "",
        "event_set": "test_set",
        "strategy": "elevate_comb_correct",
        "projection": "all_projections",
        "future_year": "two thousand eighty",
        "current_situation": {
            "projection": database.site.attrs.benefits.current_projection,
            "year": database.site.attrs.benefits.current_year,
        },
        "baseline_strategy": database.site.attrs.benefits.baseline_strategy,
        "discount_rate": 0.07,
    }

    # When user tries to create benefits calculation, it will return an error since year has wrong format
    with pytest.raises(ValueError):
        benefit = api_benefits.create_benefit(benefit_dict, database)

    # correct value of year
    benefit_dict["future_year"] = 2080
    benefit = api_benefits.create_benefit(benefit_dict, database)

    # When user tries to create benefits calculation, it will return an error since name already exists
    with pytest.raises(ValueError):
        api_benefits.save_benefit(benefit, database)

    # Change name to something new
    benefit_dict["name"] = "benefit_raise_properties_2080"
    benefit = api_benefits.create_benefit(benefit_dict, database)

    # When user presses "Check scenarios" the object will be created in memory and a dataframe will be returned
    df = api_benefits.check_benefit_scenarios(benefit, database)

    # If not all scenarios are there you should get an error
    if sum(df["scenario created"] == "No") > 0:
        with pytest.raises(ValueError):
            api_benefits.save_benefit(benefit, database)

    # Create missing scenarios
    api_benefits.create_benefit_scenarios(benefit, database)

    # Save benefit calculation
    df = api_benefits.check_benefit_scenarios(benefit, database)
    if sum(df["scenario created"] == "No") == 0:
        api_benefits.save_benefit(benefit, database)

    # Get error when the scenarios are not run
    df = api_benefits.check_benefit_scenarios(benefit, database)
    if not all(df["scenario run"]):
        with pytest.raises(RuntimeError):
            # Assert error if not yet run
            api_benefits.run_benefit("benefit_raise_properties_2080", database)

    # Create dummy data
    aggrs = database.get_aggregation_areas()
    damages_dummy = {
        "current_no_measures": 100e6,
        "current_with_strategy": 50e6,
        "future_no_measures": 300e6,
        "future_with_strategy": 180e6,
    }

    for name, row in benefit.scenarios.iterrows():
        # Create output folder
        output_path = (
            test_database_path
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
        fiat_path = output_path.joinpath("Impacts", "fiat_model", "fiat.log")
        fiat_path.parent.mkdir(parents=True)
        f = open(fiat_path, "w")
        f.write("Geom calculation are done!")
        f.close()

    api_benefits.run_benefit("benefit_raise_properties_2080", database)

    benefit = api_benefits.get_benefit("benefit_raise_properties_2080", database)
    assert (
        len(benefit.results.keys()) == 2
    )  # check if only benefits and html are produced

    # If the user edits the benefit to add costs
    benefit_dict_new = benefit_dict.copy()
    benefit_dict_new["implementation_cost"] = 30000000
    benefit_dict_new["annual_maint_cost"] = 0
    benefit = api_benefits.create_benefit(benefit_dict_new, database)
    api_benefits.edit_benefit(benefit, database)
    api_benefits.run_benefit("benefit_raise_properties_2080", database)
    benefit = api_benefits.get_benefit("benefit_raise_properties_2080", database)
    assert "costs" in benefit.results.keys()  # check if costs is in results
    assert "BCR" in benefit.results.keys()  # check if BCR is in results

    api_benefits.delete_benefit("benefit_raise_properties_2080", database)
