import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from flood_adapt.adapter.fiat_adapter import FiatColumns
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.scenario import Scenario


class TestFiatAdapter:
    @pytest.fixture(scope="class")
    def run_scenario_no_measures(self, test_db_class):
        scenario_name = "current_extreme12ft_no_measures"
        test_db_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_db_class.scenarios.get(scenario_name)
        yield test_db_class, scenario_name, scenario_obj

    @pytest.fixture(scope="class")
    def run_scenario_all_measures(self, test_db_class):
        scenario_name = "all_projections_extreme12ft_strategy_comb"
        test_db_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_db_class.scenarios.get(scenario_name)
        yield test_db_class, scenario_name, scenario_obj

    @pytest.fixture(scope="class")
    def run_scenario_raise_datum(self, test_db_class):
        scenario_name = "current_extreme12ft_raise_datum"
        test_db_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_db_class.scenarios.get(scenario_name)
        yield test_db_class, scenario_name, scenario_obj

    @pytest.fixture(scope="class")
    def run_scenario_return_periods(self, test_db_class):
        scenario_name = "current_test_set_no_measures"
        test_db_class.run_scenario(scenario_name)
        scenario_obj: Scenario = test_db_class.scenarios.get(scenario_name)
        yield test_db_class, scenario_name, scenario_obj

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

    def test_all_measures(self, run_scenario_all_measures):
        test_db, scenario_name, test_scenario = run_scenario_all_measures

        exposure_template = pd.read_csv(
            test_db.static_path / "templates" / "fiat" / "exposure" / "exposure.csv"
        )
        exposure_scenario = pd.read_csv(
            test_db.scenarios.output_path.joinpath(
                scenario_name, "Impacts", f"Impacts_detailed_{scenario_name}.csv"
            )
        )

        # check if new development area was added
        assert len(exposure_scenario) > len(exposure_template)

        # check if growth has been applied correctly
        inds1 = exposure_scenario[FiatColumns.object_id].isin(
            exposure_template[FiatColumns.object_id]
        ) & (exposure_scenario[FiatColumns.primary_object_type] != "road")
        exp1 = exposure_scenario.loc[inds1, FiatColumns.damage_structure]
        inds0 = exposure_template[FiatColumns.primary_object_type] != "road"
        exp0 = exposure_template.loc[inds0, FiatColumns.damage_structure]
        eg = test_scenario.impacts.socio_economic_change.attrs.economic_growth
        pg = (
            test_scenario.impacts.socio_economic_change.attrs.population_growth_existing
        )
        assert all(
            val1 == val0 * (eg / 100 + 1) * (pg / 100 + 1) if (val1 != 0) else True
            for val0, val1 in zip(exp0, exp1)
        )

        # check if new area max damage is implemented correctly
        inds_new_area = ~exposure_scenario[FiatColumns.object_id].isin(
            exposure_template[FiatColumns.object_id]
        )
        assert (
            pytest.approx(
                exposure_scenario.loc[inds_new_area, FiatColumns.damage_structure].sum()
            )
            == (
                test_scenario.impacts.socio_economic_change.attrs.economic_growth / 100
                + 1
            )
            * (
                test_scenario.impacts.socio_economic_change.attrs.population_growth_new
                / 100
            )
            * exposure_template.loc[:, FiatColumns.damage_structure].sum()
        )

        # check if buildings are elevated correctly
        # First get the elevate measure attributes
        aggr_label = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
        build_type = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.property_type
        elevate_val = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.elevation.value
        # Read the base flood map information
        bfes = pd.read_csv(db_path(TopLevelDir.static) / "bfe" / "bfe.csv")

        # Create a dataframe to save the initial object attributes
        exposures = exposure_template.merge(bfes, on=FiatColumns.object_id)[
            [FiatColumns.object_id, "bfe", f"{FiatColumns.ground_floor_height}_"]
        ].rename(
            columns={
                f"{FiatColumns.ground_floor_height}_": f"{FiatColumns.ground_floor_height}_1"
            }
        )
        # Merge with the adapted fiat model exposure
        exposures = exposures.merge(exposure_scenario, on=FiatColumns.object_id).rename(
            columns={
                f"{FiatColumns.ground_floor_height}_": f"{FiatColumns.ground_floor_height}_2"
            }
        )
        # Filter to only the objects affected by the measure
        exposures = exposures.loc[
            (
                exposure_scenario.loc[
                    :, f"{FiatColumns.aggr_label_default}:{aggr_label}"
                ]
                == aggr_name
            )
            & (exposure_scenario.loc[:, FiatColumns.primary_object_type] == build_type),
            :,
        ]
        exposures = exposures[
            [
                FiatColumns.object_id,
                FiatColumns.ground_elevation,
                "bfe",
                f"{FiatColumns.ground_floor_height}_1",
                f"{FiatColumns.ground_floor_height}_2",
            ]
        ]
        # Check if elevation took place correctly at each object
        for i, row in exposures.iterrows():
            # If the initial elevation is smaller than the required one it should have been elevated to than one
            if (
                row[FiatColumns.ground_elevation]
                + row[f"{FiatColumns.ground_floor_height}_1"]
                < row["bfe"] + elevate_val
            ):
                assert (
                    row[FiatColumns.ground_elevation]
                    + row[f"{FiatColumns.ground_floor_height}_2"]
                    == row["bfe"] + elevate_val
                )
            # if not it should have stated the same
            else:
                assert (
                    row[f"{FiatColumns.ground_floor_height}_2"]
                    == row[f"{FiatColumns.ground_floor_height}_1"]
                )

        # check if buildings are bought-out
        aggr_label = test_scenario.impacts.impact_strategy.measures[
            1
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.impacts.impact_strategy.measures[
            1
        ].attrs.aggregation_area_name
        build_type = test_scenario.impacts.impact_strategy.measures[
            1
        ].attrs.property_type
        inds = (
            exposure_scenario.loc[:, f"{FiatColumns.aggr_label_default}:{aggr_label}"]
            == aggr_name
        ) & (exposure_scenario.loc[:, FiatColumns.primary_object_type] == build_type)

        assert all(exposure_scenario.loc[inds, FiatColumns.damage_structure] == 0)

        # check if buildings are flood-proofed
        aggr_label = test_scenario.impacts.impact_strategy.measures[
            2
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.impacts.impact_strategy.measures[
            2
        ].attrs.aggregation_area_name
        build_type = test_scenario.impacts.impact_strategy.measures[
            2
        ].attrs.property_type
        inds1 = (
            exposure_template.loc[:, f"{FiatColumns.aggr_label_default}:{aggr_label}"]
            == aggr_name
        ) & (exposure_template.loc[:, FiatColumns.primary_object_type] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"{FiatColumns.aggr_label_default}:{aggr_label}"]
            == aggr_name
        ) & (exposure_scenario.loc[:, FiatColumns.primary_object_type] == build_type)

        assert all(
            exposure_scenario.loc[inds2, FiatColumns.fn_damage_structure]
            != exposure_template.loc[inds1, FiatColumns.fn_damage_structure]
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

        # check if buildings are elevated
        aggr_label = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
        build_type = test_scenario.impacts.impact_strategy.measures[
            0
        ].attrs.property_type
        inds1 = (
            exposure_template.loc[:, f"{FiatColumns.aggr_label_default}:{aggr_label}"]
            == aggr_name
        ) & (exposure_template.loc[:, FiatColumns.primary_object_type] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"{FiatColumns.aggr_label_default}:{aggr_label}"]
            == aggr_name
        ) & (exposure_scenario.loc[:, FiatColumns.primary_object_type] == build_type)

        assert all(
            elev1 <= elev2
            for elev1, elev2 in zip(
                exposure_template.loc[inds1, f"{FiatColumns.ground_floor_height}_"],
                exposure_scenario.loc[inds2, f"{FiatColumns.ground_floor_height}_"],
            )
        )

        assert all(
            height + elev
            >= test_scenario.impacts.impact_strategy.measures[0].attrs.elevation.value
            for height, elev in zip(
                exposure_scenario.loc[inds2, f"{FiatColumns.ground_floor_height}_"],
                exposure_scenario.loc[inds2, FiatColumns.ground_elevation],
            )
        )

    def test_return_periods(self, run_scenario_return_periods):
        test_db, scenario_name, test_scenario = run_scenario_return_periods
        assert test_scenario.impacts.has_run
