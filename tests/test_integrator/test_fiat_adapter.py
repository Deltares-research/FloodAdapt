from pathlib import Path

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"
exposure_template = pd.read_csv(
    test_database
    / "charleston"
    / "static"
    / "templates"
    / "fiat"
    / "exposure"
    / "exposure.csv"
)


def test_fiat_adapter_no_measures(cleanup_database):
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.run()

    exposure_scenario = pd.read_csv(
        test_scenario.direct_impacts.fiat_path
        / "exposure"
        / "exposure.csv"
    )

    # check if exposure is left unchanged
    assert_frame_equal(exposure_scenario, exposure_template, check_dtype=False)


# @pytest.mark.skip(reason="test needs to reviewed")
def test_fiat_adapter_measures(cleanup_database):
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.run()

    exposure_scenario = pd.read_csv(
        test_database
        / "charleston"
        / "output"
        / "results"
        / "all_projections_extreme12ft_strategy_comb"
        / "fiat_model"
        / "exposure"
        / "exposure.csv"
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
    pg = (
        test_scenario.direct_impacts.socio_economic_change.attrs.population_growth_existing
    )
    assert all(
        val1 == val0 * (eg / 100 + 1) * (pg / 100 + 1) if (val1 != 0) else True
        for val0, val1 in zip(exp0, exp1)
    )

    # check if new area max damage is implemented correctly
    inds_new_area = ~exposure_scenario["Object ID"].isin(exposure_template["Object ID"])
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


def test_fiat_return_periods(cleanup_database):
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_test_set_no_measures"
        / "current_test_set_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.run()
    assert test_scenario.direct_impacts.has_run
