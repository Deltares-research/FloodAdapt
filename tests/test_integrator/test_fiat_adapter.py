import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

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

    def test_no_measures(self, run_scenario_no_measures):
        test_db, scenario_name, scenario_obj = run_scenario_no_measures

        exposure_template = pd.read_csv(
            test_db.static_path / "templates" / "fiat" / "exposure" / "exposure.csv"
        )
        exposure_scenario = pd.read_csv(
            scenario_obj.results_path
            / "Impacts"
            / "fiat_model"
            / "exposure"
            / "exposure.csv"
        )

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
        inds1 = exposure_scenario["Object ID"].isin(exposure_template["Object ID"]) & (
            exposure_scenario["Primary Object Type"] != "road"
        )
        exp1 = exposure_scenario.loc[inds1, "Max Potential Damage: Structure"]
        inds0 = exposure_template["Primary Object Type"] != "road"
        exp0 = exposure_template.loc[inds0, "Max Potential Damage: Structure"]
        eg = test_scenario.direct_impacts.socio_economic_change.attrs.economic_growth
        pg = test_scenario.direct_impacts.socio_economic_change.attrs.population_growth_existing
        assert all(
            val1 == val0 * (eg / 100 + 1) * (pg / 100 + 1) if (val1 != 0) else True
            for val0, val1 in zip(exp0, exp1)
        )

        # check if new area max damage is implemented correctly
        inds_new_area = ~exposure_scenario["Object ID"].isin(
            exposure_template["Object ID"]
        )
        assert (
            pytest.approx(
                exposure_scenario.loc[
                    inds_new_area, "Max Potential Damage: Structure"
                ].sum()
            )
            == (
                test_scenario.direct_impacts.socio_economic_change.attrs.economic_growth
                / 100
                + 1
            )
            * (
                test_scenario.direct_impacts.socio_economic_change.attrs.population_growth_new
                / 100
            )
            * exposure_template.loc[:, "Max Potential Damage: Structure"].sum()
        )

        # check if buildings are elevated correctly
        # First get the elevate measure attributes
        aggr_label = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
        build_type = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.property_type
        elevate_val = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.elevation.value
        # Read the base flood map information

        bfes = pd.read_csv(test_db.static_path / "bfe" / "bfe.csv")

        # Create a dataframe to save the initial object attributes
        exposures = exposure_template.merge(bfes, on="Object ID")[
            ["Object ID", "bfe", "Ground Floor Height"]
        ].rename(columns={"Ground Floor Height": "Ground Floor Height 1"})
        # Merge with the adapted fiat model exposure
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
        aggr_label = test_scenario.direct_impacts.impact_strategy.measures[
            1
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.direct_impacts.impact_strategy.measures[
            1
        ].attrs.aggregation_area_name
        build_type = test_scenario.direct_impacts.impact_strategy.measures[
            1
        ].attrs.property_type
        inds = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(exposure_scenario.loc[inds, "Max Potential Damage: Structure"] == 0)

        # check if buildings are flood-proofed
        aggr_label = test_scenario.direct_impacts.impact_strategy.measures[
            2
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.direct_impacts.impact_strategy.measures[
            2
        ].attrs.aggregation_area_name
        build_type = test_scenario.direct_impacts.impact_strategy.measures[
            2
        ].attrs.property_type
        inds1 = (
            exposure_template.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_template.loc[:, "Primary Object Type"] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(
            exposure_scenario.loc[inds2, "Damage Function: Structure"]
            != exposure_template.loc[inds1, "Damage Function: Structure"]
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
        aggr_label = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_type
        aggr_name = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
        build_type = test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.property_type
        inds1 = (
            exposure_template.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_template.loc[:, "Primary Object Type"] == build_type)
        inds2 = (
            exposure_scenario.loc[:, f"Aggregation Label: {aggr_label}"] == aggr_name
        ) & (exposure_scenario.loc[:, "Primary Object Type"] == build_type)

        assert all(
            elev1 <= elev2
            for elev1, elev2 in zip(
                exposure_template.loc[inds1, "Ground Floor Height"],
                exposure_scenario.loc[inds2, "Ground Floor Height"],
            )
        )

        assert all(
            height + elev
            >= test_scenario.direct_impacts.impact_strategy.measures[
                0
            ].attrs.elevation.value
            for height, elev in zip(
                exposure_scenario.loc[inds2, "Ground Floor Height"],
                exposure_scenario.loc[inds2, "Ground Elevation"],
            )
        )

    def test_return_periods(self, run_scenario_no_measures):
        test_db, scenario_name, test_scenario = run_scenario_no_measures
        assert test_scenario.direct_impacts.has_run
