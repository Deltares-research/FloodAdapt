import pandas as pd
import pytest

from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit


# Create Benefit object using example benefit toml in test database
def test_loadFile_fromTestBenefitToml_createBenefit(test_db):
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        "benefit_raise_properties_2050",
        "benefit_raise_properties_2050.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, IBenefit)


# Create Benefit object using using example benefit toml in test database to see if test with no costs is load normally
def test_loadFile_fromTestBenefitNoCostsToml_createBenefit(test_db):
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        "benefit_raise_properties_2050_no_costs",
        "benefit_raise_properties_2050_no_costs.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, IBenefit)


# Get FileNotFoundError when the path to the benefit toml does not exist
def test_loadFile_nonExistingFile_FileNotFoundError(test_db):
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        "benefit_raise_properties_2050_random",
        "benefit_raise_properties_2050_random.toml",
    )
    with pytest.raises(FileNotFoundError):
        Benefit.load_file(benefit_path)


# Create Benefit object using using a dictionary
def test_loadDict_fromTestDict_createBenefit(test_db):
    test_dict = {
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

    benefit = Benefit.load_dict(test_dict, test_db.input_path)

    assert isinstance(benefit, IBenefit)


# Fixture to create a Benefit object
@pytest.fixture(scope="function")
def benefit_obj(test_db):
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        "benefit_raise_properties_2050",
        "benefit_raise_properties_2050.toml",
    )

    benefit = Benefit.load_file(benefit_path)
    return benefit


# Tests for when the scenarios needed for the benefit analysis are not there yet
class TestBenefitScenariosNotCreated:
    # When benefit analysis is not run yet the has_run_check method should return False
    def test_hasRunCheck_notCreated_false(self, benefit_obj):
        assert not benefit_obj.has_run_check()

    # The check_scenarios methods should always return a table with the scenarios that are needed to run the benefit analysis
    def test_checkScenarios_notCreated_table(self, benefit_obj):
        scenarios = benefit_obj.check_scenarios()
        assert isinstance(scenarios, pd.DataFrame)
        assert len(scenarios) == 4

    # When the needed scenarios are not there, the ready_to_run method should return false
    def test_readyToRun_notCreated_false(self, benefit_obj):
        assert not benefit_obj.ready_to_run()

    # When the needed scenarios are not there, the run_cost_benefit method should return a RunTimeError
    def test_runCostBenefit_notCreated_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.run_cost_benefit()
        assert (
            str(exception_info.value)
            == "Necessary scenarios have not been created yet."
        )


# Tests for when the scenarios needed for the benefit analysis are not there yet
class TestBenefitScenariosCreated:
    # Fixture to create a Benefit object
    @pytest.fixture(scope="class")
    def create_scenarios(self):
        pass
        # Create missing scenarios
        # api_benefits.create_benefit_scenarios(benefit, database)

    # When benefit analysis is not run yet the has_run_check method should return False
    def test_hasRunCheck_notRun_false(self, benefit_obj):
        assert not benefit_obj.has_run_check()

    # The check_scenarios methods should always return a table with the scenarios that are needed to run the benefit analysis
    def test_checkScenarios_notReadyToRun_table(self, benefit_obj):
        scenarios = benefit_obj.check_scenarios()
        assert isinstance(scenarios, pd.DataFrame)
        assert len(scenarios) == 4

    # When the needed scenarios are not there, the ready_to_run method should return false
    def test_readyToRun_notReadyToRun_raiseRunTimeError(self, benefit_obj):
        assert not benefit_obj.ready_to_run()

    # When the needed scenarios are not there, the run_cost_benefit method should return a RunTimeError
    def test_runCostBenefit_notReadyToRun_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.run_cost_benefit()
        assert (
            str(exception_info.value)
            == "Necessary scenarios have not been created yet."
        )
