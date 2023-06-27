import filecmp
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
import xarray as xr

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


# @pytest.mark.skip(reason="There is no sfincs.inp checked in")
def test_hazard_run_synthetic_wl():
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
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()


# @pytest.mark.skip(reason="There is no sfincs.inp checked in")
def test_hazard_run_synthetic_discharge():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_rivershape_windconst_no_measures"
        / "current_extreme12ft_rivershape_windconst_no_measures.toml"
    )

    assert test_toml.is_file()

    # use event template to get the associated Event child class
    test_scenario = Scenario.load_file(test_toml)
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()


def test_preprocess_prob_eventset():
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
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()
    bzs_file1 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0001"
        / "overland"
        / "sfincs.bzs"
    )
    bzs_file2 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0039"
        / "overland"
        / "sfincs.bzs"
    )
    assert bzs_file1.is_file()
    assert bzs_file2.is_file()
    assert ~filecmp.cmp(bzs_file1, bzs_file2)


@pytest.mark.skip(reason="Running models takes a couple of minutes")
def test_run_prob_eventset():
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
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()
    zs_file1 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0001"
        / "overland"
        / "sfincs_map.nc"
    )
    zs_file2 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0039"
        / "overland"
        / "sfincs_map.nc"
    )
    assert zs_file1.is_file()
    assert zs_file2.is_file()


@pytest.mark.skip(
    reason="Need to run models first (see above) but that takes a couple of minutes"
)
def test_rp_floodmap_calculation():
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
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.calculate_rp_floodmaps()
    nc_file = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "rp_water_level.nc"
    )
    assert nc_file.is_file()
    zs_file1 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0001"
        / "overland"
        / "sfincs_map.nc"
    )
    zs_file2 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0039"
        / "overland"
        / "sfincs_map.nc"
    )
    zs_file3 = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "event_0078"
        / "overland"
        / "sfincs_map.nc"
    )
    assert zs_file1.is_file()
    assert zs_file2.is_file()
    assert zs_file3.is_file()

    xr.open_dataset(zs_file1)
    xr.open_dataset(zs_file2)
    xr.open_dataset(zs_file3)

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))
