import filecmp
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.event import (
    Event,
)
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import (
    Site,
)

test_database = Path().absolute() / "tests" / "test_database"


@pytest.mark.skip(reason="running the model takes long")
def test_hazard_run_synthetic_wl(cleanup_database):
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


@pytest.mark.skip(reason="There is no sfincs.inp checked in")
def test_hazard_run_synthetic_discharge(cleanup_database):
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


def test_preprocess_rainfall_timeseriesfile(cleanup_database):
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
    hazard.event.attrs.rainfall.timeseries_file = "rainfall.csv"

    tt = pd.date_range(
        start=hazard.event.attrs.time.start_time,
        end=hazard.event.attrs.time.end_time,
        freq="1H",
    )
    rain = 100 * np.exp(-(((np.arange(0, len(tt), 1) - 24) / (0.25 * 12)) ** 2)).round(
        decimals=2
    )
    df = pd.DataFrame(index=tt, data=rain)
    df.to_csv(event_path.joinpath("rainfall.csv"))

    hazard.preprocess_models()

    prcp_file = hazard.simulation_paths[0].joinpath("sfincs.precip")
    assert prcp_file.is_file()

    # Delete rainfall file that was created for the test
    os.remove(event_path.joinpath("rainfall.csv"))


def test_preprocess_pump(cleanup_database):
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )
    assert test_toml.is_file()

    scenario = Scenario.load_file(test_toml)
    scenario.attrs.strategy = "pump"
    scenario.attrs.name = scenario.attrs.name.replace("no_measures", "pump")
    scenario.init_object_model()

    hazard = scenario.direct_impacts.hazard

    hazard.preprocess_models()

    drn_file = hazard.simulation_paths[0].joinpath("sfincs.drn")
    assert drn_file.is_file()

    drn_templ = scenario.database_input_path.parent.joinpath(
        "static", "templates", "overland", "sfincs.drn"
    )

    ~filecmp.cmp(drn_file, drn_templ)


@pytest.mark.skip(
    reason="hydroMT SFINCS Green Infra plug-in requires HydroMT core 0.8.0"
)
def test_preprocess_greenInfra(cleanup_database):
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
    test_scenario.attrs.strategy = "greeninfra"
    test_scenario.init_object_model()
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy.measures[0],
        GreenInfrastructure,
    )
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy.measures[1],
        GreenInfrastructure,
    )
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy.measures[2],
        GreenInfrastructure,
    )
    test_scenario.direct_impacts.hazard.preprocess_models()


@pytest.mark.skip(reason="running the model takes long")
def test_write_floodmap_geotiff(cleanup_database):
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
    test_scenario.direct_impacts.hazard.postprocess_models()

    floodmap_fn = test_scenario.direct_impacts.hazard.simulation_paths[0].joinpath(
        "floodmap.tif"
    )
    assert floodmap_fn.is_file()


def test_preprocess_prob_eventset(cleanup_database):
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


# @pytest.mark.skip(reason="Running models takes a couple of minutes")
def test_run_prob_eventset(cleanup_database):
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
def test_rp_floodmap_calculation(cleanup_database):
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


def test_multiple_rivers(cleanup_database):
    # 1) Create new site dictionary
    test_toml = test_database / "charleston" / "static" / "site" / "site.toml"

    assert test_toml.is_file()

    test_data = Site.load_file(test_toml)

    # Change river data
    name = []
    description = []
    x = []
    y = []
    mean_discharge = []
    for ii in [0, 1]:
        name.append(f"{test_data.attrs.river.name[0]}_{ii}")
        description.append(f"{test_data.attrs.river.description[0]} {ii}")
        x.append(test_data.attrs.river.x_coordinate[0] - 1000 * ii)
        y.append(test_data.attrs.river.y_coordinate[0] - 1000 * ii)
        mean_discharge.append(test_data.attrs.river.mean_discharge[0])

    test_data.attrs.river.name = name
    test_data.attrs.river.x_coordinate = x
    test_data.attrs.river.y_coordinate = y
    test_data.attrs.river.mean_discharge = mean_discharge
    test_data.attrs.river.description = description

    # Change name of reference model
    test_data.attrs.sfincs.overland_model = "overland_2_rivers"

    # 2) Create information about the two rivers
    test_event_toml = test_database / "charleston" / "input" / "events" / "extreme12ft" / "extreme12ft.toml"

    assert test_event_toml.is_file()

    test_event_data = Event.load_file(test_event_toml)

    test_event_data.attrs.river.source = ["constant", "shape"]
    test_event_data.attrs.river.constant_discharge = [{"value":4000, "units":"cfs"},{"value":None, "units":None}]
    test_event_data.attrs.river.shape_type = [None, "gaussian"]
    test_event_data.attrs.river.base_discharge = [None, 1000]
    test_event_data.attrs.river.shape_peak = [None, 2500]
    test_event_data.attrs.river.shape_duration = [None, 8]
    test_event_data.attrs.river.shape_peak_time = [None, 0]
    test_event_data.attrs.river.shape_start_time = [None, None]
    test_event_data.attrs.river.shape_end_time = [None, None]

    # 3) Make discharge boundary conditions
    

    # 4) Check discharge boundary conditions
