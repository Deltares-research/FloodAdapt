import numpy as np
import pytest

from flood_adapt.workflows.benefit_runner import Benefit

_RAND = np.random.default_rng(2021)  # Value to make sure randomizing is always the same
_TEST_NAMES = {
    "benefit_with_costs": "benefit_raise_properties_2050",
    "benefit_without_costs": "benefit_raise_properties_2050_no_costs",
}

_TEST_DICT = {
    "name": "benefit_raise_properties_2080",
    "description": "",
    "event_set": "test_set",
    "strategy": "elevate_comb_correct",
    "projection": "all_projections",
    "future_year": 2080,
    "current_situation": {"projection": "current", "year": "2023"},
    "baseline_strategy": "no_measures",
    "discount_rate": 0.07,
    "implementation_cost": 200000000,
    "annual_maint_cost": 100000,
}


# Create Benefit object using example benefit toml in test database
def test_loadfile_fromtestbenefittoml_createbenefit(test_db):
    name = "benefit_raise_properties_2050"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, Benefit)


# Create Benefit object using using example benefit toml in test database to see if test with no costs is load normally
def test_loadfile_fromtestbenefitnocoststoml_createbenefit(test_db):
    name = "benefit_raise_properties_2050_no_costs"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, Benefit)


# Get FileNotFoundError when the path to the benefit toml does not exist
def test_loadfile_nonexistingfile_filenotfounderror(test_db):
    name = "benefit_raise_properties_2050_random"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    with pytest.raises(FileNotFoundError):
        Benefit.load_file(benefit_path)


# Create Benefit object using using a dictionary
def test_loaddict_fromtestdict_createbenefit(test_db):
    benefit = Benefit(**_TEST_DICT)
    assert isinstance(benefit, Benefit)


# Save a toml from a test benefit dictionary
def test_save_fromtestdict_savetoml(test_db):
    benefit = Benefit(**_TEST_DICT)
    output_path = test_db.input_path.joinpath(
        "benefits", "test_benefit", "test_benefit.toml"
    )
    if not output_path.parent.exists():
        output_path.parent.mkdir()
    assert not output_path.exists()
    benefit.save(output_path)
    assert output_path.exists()
