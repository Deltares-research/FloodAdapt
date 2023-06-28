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

    # for visual checks uncomment those lines
    # zs1 = xr.open_dataset(zs_file1).load()
    # zs2 = xr.open_dataset(zs_file2).load()
    # zs3 = xr.open_dataset(zs_file3).load()
    # zsrp = xr.open_dataset(nc_file).load()

    # fig, ax = plt.subplots(6, 2, figsize=(12, 18))

    # ax[1, 0].pcolor(zs1.x, zs1.y, zs1.zsmax.squeeze(), vmin=0, vmax=2)
    # ax[2, 0].pcolor(zs2.x, zs2.y, zs2.zsmax.squeeze(), vmin=0, vmax=2)
    # ax[4, 0].pcolor(zs3.x, zs3.y, zs3.zsmax.squeeze(), vmin=0, vmax=2)
    # ax[0, 1].pcolor(zs1.x, zs1.y, zsrp.to_array().sel(rp=1).squeeze(), vmin=0, vmax=2)
    # ax[1, 1].pcolor(zs2.x, zs2.y, zsrp.to_array().sel(rp=2).squeeze(), vmin=0, vmax=2)
    # ax[2, 1].pcolor(zs3.x, zs3.y, zsrp.to_array().sel(rp=5).squeeze(), vmin=0, vmax=2)
    # ax[3, 1].pcolor(zs3.x, zs3.y, zsrp.to_array().sel(rp=10).squeeze(), vmin=0, vmax=2)
    # ax[4, 1].pcolor(zs3.x, zs3.y, zsrp.to_array().sel(rp=50).squeeze(), vmin=0, vmax=2)
    # ax[5, 1].pcolor(zs3.x, zs3.y, zsrp.to_array().sel(rp=100).squeeze(), vmin=0, vmax=2)
    # ax[1, 0].set_title("event_0001: 2 years")
    # ax[2, 0].set_title("event_0039: 5 years")
    # ax[4, 0].set_title("event_0078: 50 years")
    # ax[0, 1].set_title("RP=1")
    # ax[1, 1].set_title("RP=2")
    # ax[2, 1].set_title("RP=5")
    # ax[3, 1].set_title("RP=10")
    # ax[4, 1].set_title("RP=50")
    # ax[5, 1].set_title("RP=100")
    # fn = (
    #     test_database
    #     / "charleston"
    #     / "output"
    #     / "simulations"
    #     / "current_test_set_no_measures"
    #     / "floodmaps.png"
    # )
    # plt.savefig(fn, bbox_inches="tight", dpi=225)
