from pathlib import Path

import pytest

import flood_adapt.api.benefits as api_benefits
import flood_adapt.api.scenarios as api_scenarios
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

    # Runs missing scenarios
    for name, row in df.iterrows():
        if not row["scenario run"]:
            api_scenarios.run_scenario(row["scenario created"], database)

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
