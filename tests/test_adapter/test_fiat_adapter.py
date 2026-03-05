import pandas as pd
import pytest
from fiat_toolbox import get_fiat_columns
from pandas.testing import assert_frame_equal

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.workflows.scenario_runner import Scenario, ScenarioRunner
from tests.conftest import CAN_EXECUTE_SCENARIOS

_FIAT_COLUMNS = get_fiat_columns()

# mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not CAN_EXECUTE_SCENARIOS,
    reason="Only run when we can execute scenarios. Requires either a working sfincs binary, or a working docker setup",
)
class TestFiatAdapter:
    @pytest.fixture(scope="class")
    def run_scenario_no_measures(self, test_fa_class):
        scenario_name = "current_extreme12ft_no_measures"
        test_fa_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_fa_class.get_scenario(scenario_name)
        yield test_fa_class.database, scenario_name, scenario_obj

    @pytest.fixture(scope="class")
    def run_scenario_all_measures(self, test_fa_class):
        scenario_name = "all_projections_extreme12ft_strategy_comb"
        test_fa_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_fa_class.get_scenario(scenario_name)
        runner = ScenarioRunner(test_fa_class.database, scenario_obj)
        yield test_fa_class.database, scenario_name, scenario_obj, runner

    @pytest.fixture(scope="class")
    def run_scenario_raise_datum(self, test_fa_class):
        scenario_name = "current_extreme12ft_raise_datum"
        test_fa_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_fa_class.get_scenario(scenario_name)
        yield test_fa_class.database, scenario_name, scenario_obj

    @pytest.fixture(scope="class")
    def run_scenario_return_periods(self, test_fa_class):
        scenario_name = "current_test_set_no_measures"
        test_fa_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_fa_class.get_scenario(scenario_name)
        yield test_fa_class.database, scenario_name, scenario_obj

    def test_no_measures(self, run_scenario_no_measures):
        test_db, scenario_name, scenario_obj = run_scenario_no_measures

        exposure_template = pd.read_csv(
            test_db.static_path / "templates" / "fiat" / "exposure" / "exposure.csv"
        )
        path = test_db.scenarios.output_path.joinpath(
            scenario_name, "Impacts", "fiat_model", "exposure", "exposure.csv"
        )
        exposure_scenario = pd.read_csv(path)

        # check if exposure is left unchanged
        assert_frame_equal(exposure_scenario, exposure_template, check_dtype=False)

    def test_all_measures(
        self, run_scenario_all_measures: tuple[IDatabase, str, Scenario, ScenarioRunner]
    ):
        test_db, scenario_name, test_scenario, test_runner = run_scenario_all_measures
        exposure_template = pd.read_csv(
            test_db.static_path / "templates" / "fiat" / "exposure" / "exposure.csv"
        )
        exposure_scenario = pd.read_csv(
            test_db.scenarios.output_path.joinpath(
                scenario_name, "Impacts", f"Impacts_detailed_{scenario_name}.csv"
            )
        )

        socio_economic_change = test_db.projections.get(
            test_scenario.projection
        ).socio_economic_change
        strategy = test_db.strategies.get(test_scenario.strategy)

        # check if new development area was added
        assert len(exposure_scenario) > len(exposure_template)

        # check if growth has been applied correctly
        inds1 = exposure_scenario["Object ID"].isin(
            exposure_template[_FIAT_COLUMNS.object_id]
        ) & (exposure_scenario["Primary Object Type"] != "road")
        exp1 = exposure_scenario.loc[inds1, "Max Potential Damage: structure"]
        inds0 = exposure_template[_FIAT_COLUMNS.primary_object_type] != "road"
        exp0 = exposure_template.loc[
            inds0, _FIAT_COLUMNS.max_potential_damage.format(name="structure")
        ]
        eg = socio_economic_change.economic_growth
        pg = socio_economic_change.population_growth_existing
        assert all(
            val1 == val0 * (eg / 100 + 1) * (pg / 100 + 1) if (val1 != 0) else True
            for val0, val1 in zip(exp0, exp1)
        )

        # check if new area max damage is implemented correctly
        inds_new_area = ~exposure_scenario["Object ID"].isin(
            exposure_template[_FIAT_COLUMNS.object_id]
        )
        assert (
            pytest.approx(
                exposure_scenario.loc[
                    inds_new_area, "Max Potential Damage: structure"
                ].sum()
            )
            == (socio_economic_change.economic_growth / 100 + 1)
            * (socio_economic_change.population_growth_new / 100)
            * exposure_template.loc[
                :, _FIAT_COLUMNS.max_potential_damage.format(name="structure")
            ].sum()
        )

        # check if buildings are elevated correctly
        # First get the elevate measure attributes
        impact_measures = strategy.get_impact_measures()
        aggr_label = impact_measures[0].aggregation_area_type
        aggr_name = impact_measures[0].aggregation_area_name
        build_type = impact_measures[0].property_type
        elevate_val = impact_measures[0].elevation.value

        # Read the base flood map information
        bfes = pd.read_csv(db_path(TopLevelDir.static) / "bfe" / "bfe.csv")

        # Create a dataframe to save the initial object attributes
        exposures = exposure_template.merge(bfes, on=_FIAT_COLUMNS.object_id)[
            [_FIAT_COLUMNS.object_id, "bfe", _FIAT_COLUMNS.ground_floor_height]
        ].rename(columns={_FIAT_COLUMNS.ground_floor_height: "Ground Floor Height 1"})
        # Merge with the adapted fiat model exposure
        exposures = exposures.rename(columns={_FIAT_COLUMNS.object_id: "Object ID"})
        exposures = exposures.merge(exposure_scenario, on="Object ID").rename(
            columns={"Ground Floor Height": "Ground Floor Height 2"}
        )
        # Filter to only the objects affected by the measure
        exposures = exposures.loc[
            (exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name)
            & (exposure_scenario.loc[:, "Primary Object Type"] == build_type),
            :,
        ]
        exposures = exposures[
            [
                "Object ID",
                "Ground Elevation",
                "bfe",
                "Ground Floor Height 1",
                "Ground Floor Height 2",
            ]
        ]
        # Check if elevation took place correctly at each object
        for i, row in exposures.iterrows():
            # If the initial elevation is smaller than the required one it should have been elevated to than one
            if (
                row["Ground Elevation"] + row["Ground Floor Height 1"]
                < row["bfe"] + elevate_val
            ):
                assert (
                    row["Ground Elevation"] + row["Ground Floor Height 2"]
                    == row["bfe"] + elevate_val
                )
            # if not it should have stated the same
            else:
                assert row["Ground Floor Height 2"] == row["Ground Floor Height 1"]

        # check if buildings are bought-out
        aggr_label = impact_measures[1].aggregation_area_type
        aggr_name = impact_measures[1].aggregation_area_name
        build_type = impact_measures[1].property_type
        inds = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(exposure_scenario.loc[inds, "Max Potential Damage: structure"] == 0)

        # check if buildings are flood-proofed
        aggr_label = impact_measures[2].aggregation_area_type
        aggr_name = impact_measures[2].aggregation_area_name
        build_type = impact_measures[2].property_type
        inds1 = (
            exposure_template.loc[
                :, _FIAT_COLUMNS.aggregation_label.format(name=aggr_label)
            ]
            == aggr_name
        ) & (exposure_template.loc[:, _FIAT_COLUMNS.primary_object_type] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(
            exposure_scenario.loc[inds2, "Damage Function: structure"]
            != exposure_template.loc[
                inds1, _FIAT_COLUMNS.damage_function.format(name="structure")
            ]
        )

    def test_raise_datum(self, run_scenario_raise_datum):
        test_db, scenario_name, test_scenario = run_scenario_raise_datum
        exposure_template = pd.read_csv(
            test_db.static_path / "templates" / "fiat" / "exposure" / "exposure.csv"
        )
        exposure_scenario = pd.read_csv(
            test_db.scenarios.output_path.joinpath(
                scenario_name, "Impacts", f"Impacts_detailed_{scenario_name}.csv"
            )
        )
        strategy = test_db.strategies.get(test_scenario.strategy)
        impact_measures = strategy.get_impact_measures()

        # check if buildings are elevated
        aggr_label = impact_measures[0].aggregation_area_type
        aggr_name = impact_measures[0].aggregation_area_name
        build_type = impact_measures[0].property_type
        inds1 = (
            exposure_template.loc[
                :, _FIAT_COLUMNS.aggregation_label.format(name=aggr_label)
            ]
            == aggr_name
        ) & (exposure_template.loc[:, _FIAT_COLUMNS.primary_object_type] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(
            elev1 <= elev2
            for elev1, elev2 in zip(
                exposure_template.loc[inds1, _FIAT_COLUMNS.ground_floor_height],
                exposure_scenario.loc[inds2, "Ground Floor Height"],
            )
        )

        assert all(
            height + elev >= impact_measures[0].elevation.value
            for height, elev in zip(
                exposure_scenario.loc[inds2, "Ground Floor Height"],
                exposure_scenario.loc[inds2, "Ground Elevation"],
            )
        )

    def test_return_periods(self, run_scenario_return_periods):
        test_db, scenario_name, test_scenario = run_scenario_return_periods

        # TODO asserts
