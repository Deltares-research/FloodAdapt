import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import tomli

from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.benefits import IBenefit

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
def test_loadFile_fromTestBenefitToml_createBenefit(test_db):
    name = "benefit_raise_properties_2050"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, IBenefit)


# Create Benefit object using using example benefit toml in test database to see if test with no costs is load normally
def test_loadFile_fromTestBenefitNoCostsToml_createBenefit(test_db):
    name = "benefit_raise_properties_2050_no_costs"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    benefit = Benefit.load_file(benefit_path)

    assert isinstance(benefit, IBenefit)


# Get FileNotFoundError when the path to the benefit toml does not exist
def test_loadFile_nonExistingFile_FileNotFoundError(test_db):
    name = "benefit_raise_properties_2050_random"
    benefit_path = test_db.input_path.joinpath(
        "benefits",
        name,
        f"{name}.toml",
    )

    with pytest.raises(FileNotFoundError):
        Benefit.load_file(benefit_path)


# Create Benefit object using using a dictionary
def test_loadDict_fromTestDict_createBenefit(test_db):
    benefit = Benefit.load_dict(_TEST_DICT)

    assert isinstance(benefit, IBenefit)


# Save a toml from a test benefit dictionary
def test_save_fromTestDict_saveToml(test_db):
    benefit = Benefit.load_dict(_TEST_DICT)
    output_path = test_db.input_path.joinpath(
        "benefits", "test_benefit", "test_benefit.toml"
    )
    if not output_path.parent.exists():
        output_path.parent.mkdir()
    assert not output_path.exists()
    benefit.save(output_path)
    assert output_path.exists()


# Tests for when the scenarios needed for the benefit analysis are not there yet
class TestBenefitScenariosNotCreated:
    # Fixture to create a Benefit object
    @pytest.fixture(scope="function")
    def benefit_obj(self, test_db_class):
        test_db = test_db_class
        name = "benefit_raise_properties_2050"
        benefit_path = test_db.input_path.joinpath(
            "benefits",
            name,
            f"{name}.toml",
        )

        benefit = Benefit.load_file(benefit_path)
        yield benefit

    # When benefit analysis is not run yet the has_run_check method should return False
    def test_hasRunCheck_notCreated_false(self, benefit_obj):
        assert not benefit_obj.has_run_check()

    # The check_scenarios methods should always return a table with the scenarios that are needed to run the benefit analysis
    def test_checkScenarios_notCreated_scenariosTable(self, benefit_obj):
        scenarios = benefit_obj.check_scenarios()
        assert isinstance(scenarios, pd.DataFrame)
        assert len(scenarios) == 4
        assert "No" in scenarios["scenario created"].to_list()
        assert all(scenarios["event"] == benefit_obj.site_info.attrs.benefits.event_set)
        assert (
            scenarios.loc["current_no_measures", "strategy"]
            == benefit_obj.site_info.attrs.benefits.baseline_strategy
        )
        assert (
            scenarios.loc["future_no_measures", "strategy"]
            == benefit_obj.site_info.attrs.benefits.baseline_strategy
        )
        assert (
            scenarios.loc["current_with_strategy", "strategy"]
            == benefit_obj.attrs.strategy
        )
        assert (
            scenarios.loc["future_with_strategy", "strategy"]
            == benefit_obj.attrs.strategy
        )
        assert (
            scenarios.loc["current_no_measures", "projection"]
            == benefit_obj.site_info.attrs.benefits.current_projection
        )
        assert (
            scenarios.loc["future_no_measures", "projection"]
            == benefit_obj.attrs.projection
        )
        assert (
            scenarios.loc["current_with_strategy", "projection"]
            == benefit_obj.site_info.attrs.benefits.current_projection
        )
        assert (
            scenarios.loc["future_with_strategy", "projection"]
            == benefit_obj.attrs.projection
        )

    # When the needed scenarios are not run yet, the ready_to_run method should return false
    def test_readyToRun_notCreated_false(self, benefit_obj):
        assert not benefit_obj.ready_to_run()

    # When the needed scenarios are not run yet, the run_cost_benefit method should return a RunTimeError
    def test_runCostBenefit_notCreated_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.run_cost_benefit()

        assert (
            str(exception_info.value)
            == "Necessary scenarios have not been created yet."
        )

    # When the benefit analysis not run yet, the get_output method should return a RunTimeError
    def test_getOutput_notRun_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.results
        assert "Cannot read output since benefit analysis" in str(exception_info.value)


# Tests for when the scenarios needed for the benefit analysis are created but not run
class TestBenefitScenariosCreated:
    # Fixture to create a Benefit object and create missing scenarios
    @pytest.fixture(scope="class", autouse=True)
    def benefit_obj(self, test_db_class):
        test_db = test_db_class
        name = "benefit_raise_properties_2050"
        benefit_path = test_db.input_path.joinpath(
            "benefits",
            name,
            f"{name}.toml",
        )

        benefit = Benefit.load_file(benefit_path)
        # Create missing scenarios
        test_db.create_benefit_scenarios(benefit)
        yield benefit

    # When benefit analysis is not run yet, the has_run_check method should return False
    def test_hasRunCheck_notRun_false(self, benefit_obj):
        assert not benefit_obj.has_run_check()

    # The check_scenarios methods should always return a table with the scenarios that are needed to run the benefit analysis
    def test_checkScenarios_notReadyToRun_scenariosTable(self, benefit_obj):
        scenarios = benefit_obj.check_scenarios()
        assert isinstance(scenarios, pd.DataFrame)
        assert len(scenarios) == 4
        assert "No" not in scenarios["scenario created"].to_list()

    # When the needed scenarios are not run yet, the ready_to_run method should return false
    def test_readyToRun_notReadyToRun_raiseRunTimeError(self, benefit_obj):
        assert not benefit_obj.ready_to_run()

    # When the needed scenarios are not run yet, the run_cost_benefit method should return a RunTimeError
    def test_runCostBenefit_notReadyToRun_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.run_cost_benefit()
        assert (
            "need to be run before the cost-benefit analysis can be performed"
            in str(exception_info.value)
        )

    # When the benefit analysis not run yet, the get_output method should return a RunTimeError
    def test_getOutput_notRun_raiseRunTimeError(self, benefit_obj):
        with pytest.raises(RuntimeError) as exception_info:
            benefit_obj.results
        assert "Cannot read output since benefit analysis" in str(exception_info.value)


# Tests for when the scenarios needed for the benefit analysis are run
@pytest.mark.parametrize("benefit_name", _TEST_NAMES.keys(), scope="class")
class TestBenefitScenariosRun:
    # Fixture to create a Benefit object, missing scenarios and scenarios output
    @pytest.fixture(scope="class")
    def prepare_outputs(self, test_db_class, benefit_name):
        benefit_name = _TEST_NAMES[benefit_name]
        test_db = test_db_class
        benefit_path = test_db.input_path.joinpath(
            "benefits",
            benefit_name,
            f"{benefit_name}.toml",
        )

        benefit = Benefit.load_file(benefit_path)
        # Create missing scenarios
        test_db.create_benefit_scenarios(benefit)

        # Create dummy results to use for benefit analysis
        damages_dummy = {
            "current_no_measures": 100e6,
            "current_with_strategy": 50e6,
            "future_no_measures": 300e6,
            "future_with_strategy": 180e6,
        }
        # Get aggregation areas of test database
        aggrs = test_db.static.get_aggregation_areas()

        # Iterate through the 4 scenarios
        for name, row in benefit.scenarios.iterrows():
            # Create output folder
            output_path = (
                test_db.input_path.parent
                / "output"
                / "scenarios"
                / row["scenario created"]
            )
            if not output_path.exists():
                output_path.mkdir(parents=True)
            # Create dummy building impact output csv file
            fiat_path = output_path.joinpath(
                "Impacts", f"Impacts_detailed_{row['scenario created']}.csv"
            )
            if not fiat_path.parent.exists():
                fiat_path.parent.mkdir()
            dummy_impacts = pd.DataFrame()
            dummy_impacts.to_csv(fiat_path)
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
                generator = np.random.default_rng()
                dmgs = generator.random(len(aggr))
                dmgs = dmgs / dmgs.sum() * damages_dummy[name]

                dict0 = {
                    "Description": ["", ""],
                    "Show In Metrics Table": ["TRUE", "TRUE"],
                    "Long Name": ["", ""],
                }

                for i, aggr_area in enumerate(aggr["name"]):
                    dict0[aggr_area] = [dmgs[i], _RAND.normal(1, 0.2) * dmgs[i]]

                dummy_metrics_aggr = pd.DataFrame(
                    dict0, index=["ExpectedAnnualDamages", "EWEAD"]
                ).T

                dummy_metrics_aggr.to_csv(
                    output_path.joinpath(
                        f"Infometrics_{row['scenario created']}_{aggr_type}.csv"
                    )
                )

        yield benefit, aggrs

    # When benefit analysis is not run yet, the has_run_check method should return False
    def test_hasRunCheck_notRun_false(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        assert not benefit_obj.has_run_check()

    # The check_scenarios methods should always return a table with the scenarios that are needed to run the benefit analysis
    def test_checkScenarios_ReadyToRun_scenariosTable(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]

        scenarios = benefit_obj.check_scenarios()
        assert isinstance(scenarios, pd.DataFrame)
        assert len(scenarios) == 4
        assert "No" not in scenarios["scenario created"].to_list()

    # When the needed scenarios are run, the ready_to_run method should return true
    def test_readyToRun_readyToRun_true(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        assert benefit_obj.ready_to_run()

    # the cba method should run the cost benefit analysis for the whole region
    def test_cba_readyToRun_correctOutput(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        benefit_obj.cba()

        # assert if individual output files are there
        time_series_path = benefit_obj.results_path.joinpath("time_series.csv")
        results_path = benefit_obj.results_path.joinpath("results.toml")
        assert time_series_path.exists()
        assert results_path.exists()
        assert benefit_obj.results_path.joinpath("benefits.html").exists()

        # assert if time_series.csv has correct data
        time_series = pd.read_csv(time_series_path)  # read csv

        main_columns = [
            "year",
            "risk_no_measures",
            "risk_with_strategy",
            "benefits",
            "benefits_discounted",
        ]
        cost_columns = ["costs", "costs_discounted", "profits", "profits_discounted"]

        assert set(main_columns).issubset(time_series.columns)
        assert (
            time_series["year"].min()
            == benefit_obj.site_info.attrs.benefits.current_year
        )
        assert time_series["year"].max() == benefit_obj.attrs.future_year
        assert (
            len(time_series)
            == benefit_obj.attrs.future_year
            - benefit_obj.site_info.attrs.benefits.current_year
            + 1
        )

        # assert if results.toml has correct values
        with open(results_path, mode="rb") as fp:
            results = tomli.load(fp)

        # assert if time-series and totals are consistent
        assert results["benefits"] == time_series["benefits_discounted"].sum()

        # assert if results are equal to the expected values based on the input
        assert pytest.approx(results["benefits"], 2) == 963433925

        # assert if cost specific output is correctly presented
        if benefit_obj.attrs.implementation_cost:
            assert set(cost_columns).issubset(time_series.columns)
            assert results["costs"] == time_series["costs_discounted"].sum()
            assert pytest.approx(results["costs"], 2) == 201198670
            assert (
                pytest.approx(results["BCR"], 2)
                == results["benefits"] / results["costs"]
            )
            assert pytest.approx(results["BCR"], 2) == 4.79
            assert pytest.approx(results["NPV"], 2) == 762235253
            assert pytest.approx(results["IRR"], 2) == 0.394
        else:
            assert not set(cost_columns).issubset(time_series.columns)
            assert "costs" not in results
            assert "BCR" not in results
            assert "NPV" not in results
            assert "IRR" not in results

    # the cba_aggregation method should run the cost benefit analysis for each individual aggregation type
    def test_cbaAggregation_ReadyToRun_correctOutput(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        aggrs = prepare_outputs[1]
        benefit_obj.cba_aggregation()
        # loop through aggregation types
        for aggr_type in benefit_obj.site_info.attrs.fiat.aggregation:
            # assert existence of output files
            csv_path = benefit_obj.results_path.joinpath(
                f"benefits_{aggr_type.name}.csv"
            )
            gpkg_path = benefit_obj.results_path.joinpath(
                f"benefits_{aggr_type.name}.gpkg"
            )
            assert csv_path.exists()
            assert gpkg_path.exists()
            # assert correct structure of table
            agg_results = pd.read_csv(csv_path)
            assert "Benefits" in agg_results.columns
            if aggr_type.equity:
                assert "Equity Weighted Benefits" in agg_results.columns
            assert len(agg_results) == len(aggrs[aggr_type.name])
            # assert correct total benefits
            assert pytest.approx(agg_results["Benefits"].sum(), 2) == 963433925
            # assert existence and content of geopackages
            polygons = gpd.read_file(gpkg_path)
            assert len(polygons) == len(aggrs[aggr_type.name])

    # When the benefit analysis is run, the get_output method should return correct outputs
    def test_getOutput_Run_correctOutput(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        benefit_obj = prepare_outputs[0]
        benefit_obj.cba()
        results = benefit_obj.results
        assert hasattr(benefit_obj, "_results")
        assert "html" in results

    # When the needed scenarios are run, the run_cost_benefit method should run the benefit analysis and save the results
    def test_runCostBenefit_ReadyToRun_raiseRunTimeError(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        benefit_obj.run_cost_benefit()

        # get results
        results_path = benefit_obj.results_path.joinpath("results.toml")
        with open(results_path, mode="rb") as fp:
            results = tomli.load(fp)
        # get aggregation
        for aggr_type in benefit_obj.site_info.attrs.fiat.aggregation:
            csv_agg_results = pd.read_csv(
                benefit_obj.results_path.joinpath(f"benefits_{aggr_type.name}.csv")
            )
            tot_benefits_agg = csv_agg_results["Benefits"].sum()

            # assert if the results per aggregation area sum to the same total as the basic calculation
            assert pytest.approx(tot_benefits_agg, 2) == results["benefits"]

    # When benefit analysis is run already, the has_run_check method should return True
    def test_hasRunCheck_Run_true(self, prepare_outputs):
        benefit_obj = prepare_outputs[0]
        benefit_obj.run_cost_benefit()
        assert benefit_obj.has_run_check()
