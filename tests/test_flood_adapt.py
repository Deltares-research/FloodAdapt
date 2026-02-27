import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from flood_adapt.flood_adapt import FloodAdapt
from flood_adapt.misc.exceptions import (
    AlreadyExistsError,
)
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.events.hurricane import HurricaneEvent
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.benefit_runner import BenefitRunner
from tests.conftest import IS_WINDOWS
from tests.data.create_test_input import create_event_set_with_hurricanes
from tests.test_adapter.test_sfincs_adapter import mock_meteohandler_read
from tests.test_objects.test_events.test_eventset import (
    test_eventset,
    test_sub_event,
)
from tests.test_objects.test_events.test_historical import (
    setup_nearshore_event,
)
from tests.test_objects.test_events.test_hurricane import setup_hurricane_event
from tests.test_objects.test_events.test_synthetic import test_event_all_synthetic
from tests.test_objects.test_measures.test_measures import (
    test_buyout,
    test_elevate,
    test_floodproof,
    test_floodwall,
    test_green_infra,
    test_pump,
)

# To stop ruff from deleting these 'unused' imports
__all__ = [
    # Events
    "test_eventset",
    "test_sub_event",
    "test_event_all_synthetic",
    "create_event_set_with_hurricanes",
    "setup_nearshore_event",
    "setup_hurricane_event",
    # Mock
    "mock_meteohandler_read",
    # Measures
    "test_buyout",
    "test_elevate",
    "test_floodproof",
    "test_floodwall",
    "test_pump",
    "test_green_infra",
]


@pytest.fixture(scope="session")
def get_rng():
    yield np.random.default_rng(2021)


@pytest.mark.skipif(
    not IS_WINDOWS,
    reason="Only run on windows where we have a working sfincs binary",
)
@pytest.mark.integration
class TestScenarios:
    @pytest.fixture()
    def setup_nearshore_scenario(self, test_fa: FloodAdapt, setup_nearshore_event):
        test_fa.save_event(setup_nearshore_event)

        scn = Scenario(
            name="gauged_nearshore",
            description="current_extreme12ft_no_measures",
            event=setup_nearshore_event.name,
            projection="current",
            strategy="no_measures",
        )
        return scn

    @pytest.fixture()
    def setup_hurricane_scenario(
        self,
        test_fa: FloodAdapt,
        setup_hurricane_event: HurricaneEvent,
        mock_meteohandler_read,
    ) -> tuple[Scenario, HurricaneEvent]:
        event = setup_hurricane_event
        scn = Scenario(
            name="hurricane",
            event=event.name,
            projection="current",
            strategy="no_measures",
        )
        test_fa.save_event(event)

        return scn, event

    @pytest.fixture()
    def setup_synthetic_scenario(self, test_fa: FloodAdapt, test_event_all_synthetic):
        test_fa.save_event(test_event_all_synthetic)

        scn = Scenario(
            name="synthetic",
            event=test_event_all_synthetic.name,
            projection="current",
            strategy="no_measures",
        )
        return scn

    @pytest.fixture()
    def setup_eventset_scenario(
        self, test_fa: FloodAdapt, dummy_projection, dummy_strategy, test_eventset
    ):
        test_fa.save_projection(dummy_projection)
        test_fa.save_strategy(dummy_strategy)
        test_fa.save_event(test_eventset)

        scn = Scenario(
            name="test_risk_scenario_with_hurricanes",
            event=test_eventset.name,
            projection=dummy_projection.name,
            strategy=dummy_strategy.name,
        )
        return test_fa, scn, test_eventset

    @pytest.mark.skip(
        reason="Skipped until METEO forcing is fixed in hydromt-sfincs 1.3.0",
    )
    def test_run_offshore_scenario(
        self, test_fa: FloodAdapt, setup_offshore_meteo_scenario
    ):
        test_fa.save_scenario(setup_offshore_meteo_scenario)
        test_fa.run_scenario(setup_offshore_meteo_scenario.name)

        assert finished_file_exists(
            test_fa.database.scenarios.output_path / setup_offshore_meteo_scenario.name
        )

    def test_run_nearshore_scenario(
        self, test_fa: FloodAdapt, setup_nearshore_scenario
    ):
        test_fa.save_scenario(setup_nearshore_scenario)
        test_fa.run_scenario(setup_nearshore_scenario.name)

        assert finished_file_exists(
            test_fa.database.scenarios.output_path / setup_nearshore_scenario.name
        )

    def test_run_synthetic_scenario(
        self, test_fa: FloodAdapt, setup_synthetic_scenario
    ):
        test_fa.save_scenario(setup_synthetic_scenario)
        test_fa.run_scenario(setup_synthetic_scenario.name)

        assert finished_file_exists(
            test_fa.database.scenarios.output_path / setup_synthetic_scenario.name
        )

    def test_run_hurricane_scenario(
        self, test_fa: FloodAdapt, setup_hurricane_scenario
    ):
        scn, event = setup_hurricane_scenario
        test_fa.save_scenario(scn)
        test_fa.run_scenario(scn.name)

        assert finished_file_exists(test_fa.database.scenarios.output_path / scn.name)

    def test_run_eventset_scenario(self, test_fa: FloodAdapt, setup_eventset_scenario):
        test_fa, scn, event_set = setup_eventset_scenario
        test_fa.save_scenario(scn)
        test_fa.run_scenario(scn.name)

        assert finished_file_exists(test_fa.database.scenarios.output_path / scn.name)


@pytest.mark.skipif(
    not IS_WINDOWS,
    reason="Only run on windows where we have a working sfincs binary",
)
@pytest.mark.integration
class TestOutput:
    @pytest.fixture(scope="class")
    def completed_scenario(self, test_fa_class: FloodAdapt):
        scenario_name = "current_extreme12ft_no_measures"
        test_fa_class.run_scenario(scenario_name)
        yield test_fa_class, scenario_name

    def test_impact_metrics(self, completed_scenario: tuple[FloodAdapt, str]):
        test_fa, scn_name = completed_scenario
        metrics = test_fa.get_infometrics(scn_name)
        assert isinstance(metrics, pd.DataFrame)

    def test_impact_footprints(self, completed_scenario: tuple[FloodAdapt, str]):
        test_fa, scn_name = completed_scenario
        footprints = test_fa.get_building_footprint_impacts(scn_name)
        assert isinstance(footprints, gpd.GeoDataFrame)

    def test_impact_get_aggregation(self, completed_scenario: tuple[FloodAdapt, str]):
        test_fa, scn_name = completed_scenario
        aggr_areas = test_fa.get_aggregated_impacts(scn_name)
        assert isinstance(aggr_areas, dict)


class TestStatic:
    def test_buildings(self, test_fa: FloodAdapt):
        assert isinstance(test_fa.get_building_geometries(), gpd.GeoDataFrame)

    def test_aggr_areas(self, test_fa: FloodAdapt):
        aggr_areas = test_fa.get_aggregation_areas()

        assert isinstance(aggr_areas, dict)
        assert isinstance(aggr_areas["aggr_lvl_1"], gpd.GeoDataFrame)

    def test_building_types(self, test_fa: FloodAdapt):
        types = test_fa.get_building_types()
        expected_types = ["RES", "COM", "all"]

        assert isinstance(types, list)
        assert len(types) == 3
        assert all(t in types for t in expected_types)

    def test_existing_structures(self, test_fa: FloodAdapt):
        structures = test_fa.get_existing_structures()
        assert isinstance(structures, gpd.GeoDataFrame)


class TestBenefits:
    @pytest.mark.skip(reason="fix this test")
    def test_benefit(self, test_fa: FloodAdapt, get_rng):
        # Inputs for benefit calculation
        # Name given already exists to do test for error capture
        config = test_fa.database.site.fiat.benefits
        benefit_dict = {
            "name": "benefit_raise_properties_2050",
            "description": "",
            "event_set": "test_set",
            "strategy": "elevate_comb_correct",
            "projection": "all_projections",
            "future_year": "two thousand eighty",
            "current_situation": {
                "projection": config.current_projection,
                "year": config.current_year,
            },
            "baseline_strategy": config.baseline_strategy,
            "discount_rate": 0.07,
        }

        # When user tries to create benefits calculation, it will return an error since year has wrong format
        with pytest.raises(ValueError):
            benefit = test_fa.create_benefit(benefit_dict)

        # correct value of year
        benefit_dict["future_year"] = 2080
        benefit = test_fa.create_benefit(benefit_dict)

        # When user tries to create benefits calculation, it will return an error since name already exists
        with pytest.raises(AlreadyExistsError):
            test_fa.save_benefit(benefit)

        # Change name to something new
        benefit_dict["name"] = "benefit_raise_properties_2080"
        benefit = test_fa.create_benefit(benefit_dict)

        # When user presses "Check scenarios" the object will be created in memory and a dataframe will be returned
        df = test_fa.check_benefit_scenarios(benefit)

        # If not all scenarios are there you should get an error
        if sum(df["scenario created"] == "No") > 0:
            with pytest.raises(ValueError):
                test_fa.save_benefit(benefit)

        # Create missing scenarios
        test_fa.create_benefit_scenarios(benefit)

        # Save benefit calculation
        df = test_fa.check_benefit_scenarios(benefit)
        if sum(df["scenario created"] == "No") == 0:
            test_fa.save_benefit(benefit)

        # Get error when the scenarios are not run
        df = test_fa.check_benefit_scenarios(benefit)
        if not all(df["scenario run"]):
            with pytest.raises(RuntimeError):
                # Assert error if not yet run
                test_fa.run_benefit("benefit_raise_properties_2080")

        # Create dummy data
        aggrs = test_fa.get_aggregation_areas()
        damages_dummy = {
            "current_no_measures": 100e6,
            "current_with_strategy": 50e6,
            "future_no_measures": 300e6,
            "future_with_strategy": 180e6,
        }

        runner = BenefitRunner(test_fa.database, benefit)

        for name, row in runner.scenarios.iterrows():
            # Create output folder
            output_path = (
                test_fa.database.output_path / "scenarios" / row["scenario created"]
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
            for aggr_type, aggr in aggrs.items():
                # Generate random distribution of damage per aggregation area
                rng = np.random.default_rng(seed=2024)
                dmgs = rng.random(len(aggr))
                dmgs = dmgs / dmgs.sum() * damages_dummy[name]

                dict0 = {
                    "Description": ["", ""],
                    "Show In Metrics Table": ["TRUE", "TRUE"],
                    "Long Name": ["", ""],
                }

                for i, aggr_area in enumerate(aggr["name"]):
                    dict0[aggr_area] = [dmgs[i], get_rng.normal(1, 0.2) * dmgs[i]]

                dummy_metrics_aggr = pd.DataFrame(
                    dict0, index=["ExpectedAnnualDamages", "EWEAD"]
                ).T

                dummy_metrics_aggr.to_csv(
                    output_path.joinpath(
                        f"Infometrics_{row['scenario created']}_{aggr_type}.csv"
                    )
                )
            fiat_path = output_path.joinpath("Impacts", "fiat_model", "fiat.log")
            fiat_path.parent.mkdir(parents=True, exist_ok=True)
            f = open(fiat_path, "w")
            f.write("Geom calculation are done!")
            f.close()

        test_fa.run_benefit("benefit_raise_properties_2080")

        benefit = test_fa.get_benefit("benefit_raise_properties_2080")
        runner = BenefitRunner(test_fa.database, benefit)
        assert (
            len(runner.results.keys()) == 2
        )  # check if only benefits and html are produced

        # If the user edits the benefit to add costs
        benefit_dict_new = benefit_dict.copy()
        benefit_dict_new["implementation_cost"] = 30000000
        benefit_dict_new["annual_maint_cost"] = 0
        benefit = test_fa.create_benefit(benefit_dict_new)
        test_fa.save_benefit(benefit, overwrite=True)
        test_fa.run_benefit("benefit_raise_properties_2080")

        benefit = test_fa.get_benefit("benefit_raise_properties_2080")
        runner = BenefitRunner(test_fa.database, benefit)
        assert "costs" in runner.results.keys()  # check if costs is in results
        assert "BCR" in runner.results.keys()  # check if BCR is in results

        test_fa.delete_benefit("benefit_raise_properties_2080")
