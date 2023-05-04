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


def test_fiat_adapter_no_measures():
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
    test_scenario.init_object_model()
    # TODO: Hazard class should check if the hazard simulation has already been run when initialized
    test_scenario.direct_impacts.hazard.has_run = True  # manually change this for now
    test_scenario.direct_impacts.run_fiat()

    exposure_scenario = pd.read_csv(
        test_database
        / "charleston"
        / "output"
        / "results"
        / "current_extreme12ft_no_measures"
        / "fiat_model"
        / "exposure"
        / "exposure.csv"
    )

    # check if exposure is left unchanged
    assert_frame_equal(exposure_scenario, exposure_template, check_dtype=False)


def test_fiat_adapter_measures():
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
    test_scenario.init_object_model()
    # TODO: Hazard class should check if the hazard simulation has already been run when initialized
    test_scenario.direct_impacts.hazard.has_run = True  # manually change this for now
    test_scenario.direct_impacts.run_fiat()

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
    common_inds = exposure_scenario["Object ID"].isin(exposure_template["Object ID"])
    assert (
        exposure_scenario.loc[common_inds, "Max Potential Damage: Structure"].sum()
        == (
            test_scenario.direct_impacts.socio_economic_change.attrs.economic_growth
            / 100
            + 1
        )
        * (
            test_scenario.direct_impacts.socio_economic_change.attrs.population_growth_existing
            / 100
            + 1
        )
        * exposure_template.loc[:, "Max Potential Damage: Structure"].sum()
    )
    # check if new area max damage is implemented correctly
    assert (
        pytest.approx(
            exposure_scenario.loc[~common_inds, "Max Potential Damage: Structure"].sum()
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
    inds1 = exposure_template.loc[
        :,
        f"Aggregation Label: {test_scenario.direct_impacts.impact_strategy.measures[0].attrs.aggregation_area_type}",
    ] == (
        test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
    )
    inds2 = exposure_scenario.loc[
        :,
        f"Aggregation Label: {test_scenario.direct_impacts.impact_strategy.measures[0].attrs.aggregation_area_type}",
    ] == (
        test_scenario.direct_impacts.impact_strategy.measures[
            0
        ].attrs.aggregation_area_name
    )

    assert all(
        elev1 <= elev2
        for elev1, elev2 in zip(
            exposure_template.loc[inds1, "Ground Floor Height"],
            exposure_scenario.loc[inds2, "Ground Floor Height"],
        )
    )
