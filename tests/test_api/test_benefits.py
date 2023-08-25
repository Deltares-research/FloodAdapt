import shutil
from pathlib import Path

import pandas as pd
import pytest

import flood_adapt.api.benefits as api_benefits
import flood_adapt.api.startup as api_startup

test_database_path = Path().absolute() / "tests" / "test_database"
site_name = "charleston"


def test_benefit(cleanup_database):
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

    # When user presses add benefit and chooses the values
    with pytest.raises(ValueError):
        # Assert error if the event is not a correct value
        benefit = api_benefits.create_benefit(benefit_dict, database)
    # correct value
    benefit_dict["future_year"] = 2080
    benefit = api_benefits.create_benefit(benefit_dict, database)

    with pytest.raises(ValueError):
        # Assert error if name already exists
        api_benefits.save_benefit(benefit, database)

    # Change name to something new
    benefit_dict["name"] = "benefit_raise_properties_2080"

    # When user presses "Check scenarios" the object will be created in memory and a dataframe will be returned
    benefit = api_benefits.create_benefit(benefit_dict, database)
    df = api_benefits.check_benefit_scenarios(benefit, database)
    if sum(df["scenario created"] == "No") > 0:
        api_benefits.create_benefit_scenarios(benefit, database)

    df = api_benefits.check_benefit_scenarios(benefit, database)
    if sum(df["scenario created"] == "No") == 0:
        with pytest.raises(ValueError):
            api_benefits.save_benefit(benefit, database)

    with pytest.raises(RuntimeError):
        # Assert error if not yet run
        api_benefits.run_benefit("benefit_raise_properties_2080", database)

    # Simulate FIAT run by creating the results folder for each run and adding a csv with a total EAD
    EADs = pd.Series(
        {
            "current_no_measures": 10000000,
            "current_with_strategy": 3000000,
            "future_no_measures": 16000000,
            "future_with_strategy": 5000000,
        }
    )

    results_path = test_database_path.joinpath("charleston", "output", "results")
    for index, scenario in benefit.scenarios.iterrows():
        res_scn_path = results_path.joinpath(scenario["scenario created"]).joinpath(
            "fiat_model"
        )
        res_scn_path.mkdir(parents=True)

        df = pd.DataFrame({"EAD": EADs[index]}, index=[0])
        df.to_csv(res_scn_path.joinpath("metrics.csv"), index=False)

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
    # Delete created files
    scenarios_path = test_database_path.joinpath("charleston", "input", "scenarios")
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

    api_benefits.delete_benefit("benefit_raise_properties_2080", database)
