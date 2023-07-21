import filecmp
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


@pytest.mark.skip(reason="running the model takes long")
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


def test_preprocess_rainfall_timeseriesfile():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )
    event_path = test_database.joinpath("charleston", "input", "events", "extreme12ft")
    assert test_toml.is_file()

    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()

    hazard = scenario.direct_impacts.hazard
    hazard.event.attrs.rainfall.source = "timeseries"
    hazard.event.attrs.rainfall.timeseries_file = "rain.csv"

    tt = pd.date_range(
        start=hazard.event.attrs.time.start_time,
        end=hazard.event.attrs.time.end_time,
        freq="1H",
    )
    rain = 100 * np.exp(-(((np.arange(0, len(tt), 1) - 24) / (0.25 * 12)) ** 2)).round(
        decimals=2
    )
    df = pd.DataFrame(index=tt, data=rain)
    df.to_csv(event_path.joinpath("rain.csv"))

    hazard.preprocess_models()

    prcp_file = hazard.simulation_paths[0].joinpath("sfincs.precip")
    assert prcp_file.is_file()

    # Delete rainfall file that was created for the test
    os.remove(event_path.joinpath("rain.csv"))


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
    # test_scenario.direct_impacts.hazard.calculate_rp_floodmaps()
    nc_file = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "rp_water_level.nc"
    )
    assert nc_file.is_file()
    zsrp = xr.open_dataset(nc_file).load()
    frequencies = test_scenario.direct_impacts.hazard.frequencies

    zs = []
    event_set = test_scenario.direct_impacts.hazard.event_set
    for ii, event in enumerate(event_set):
        zs_file = (
            test_database
            / "charleston"
            / "output"
            / "simulations"
            / "current_test_set_no_measures"
            / event.attrs.name
            / "overland"
            / "sfincs_map.nc"
        )
        assert zs_file.is_file()
        zs.append(xr.open_dataset(zs_file).load())
        # below doesn't work, probably because of small round-off errors, perform visual inspection
        # if 1.0 / frequencies[ii] in zsrp.rp:
        #     assert np.equal(
        #         zs.zsmax.squeeze().to_numpy(),
        #         zsrp.sel(rp=1.0 / frequencies[ii]).to_array().to_numpy(),
        #     ).all()

    # for visual checks uncomment those lines (also imports at the top)
    fig, ax = plt.subplots(len(zsrp.rp), 2, figsize=(12, 18))
    for ii, event in enumerate(event_set):
        ax[np.max([1, 2 * ii]), 0].pcolor(
            zs[ii].x, zs[ii].y, zs[ii].zsmax.squeeze(), vmin=0, vmax=2
        )
        ax[np.max([1, 2 * ii]), 0].set_title(
            f"{event_set[ii].attrs.name}: {int(1/frequencies[ii])} years"
        )
    for jj, rp in enumerate(zsrp.rp):
        ax[jj, 1].pcolor(
            zs[0].x, zs[0].y, zsrp.sel(rp=rp).to_array().squeeze(), vmin=0, vmax=2
        )
        ax[jj, 1].set_title(f"RP={int(rp)}")
    # save png file
    fn = (
        test_database
        / "charleston"
        / "output"
        / "simulations"
        / "current_test_set_no_measures"
        / "floodmaps.png"
    )
    plt.savefig(fn, bbox_inches="tight", dpi=225)
