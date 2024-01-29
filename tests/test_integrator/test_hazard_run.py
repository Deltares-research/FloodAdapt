import filecmp
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge, UnitfulIntensity
from flood_adapt.object_model.scenario import Scenario


@pytest.fixture()
def test_scenarios(test_db):
    test_tomls = [
        test_db.input_path
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml",
        test_db.input_path
        / "scenarios"
        / "current_extreme12ft_rivershape_windconst_no_measures"
        / "current_extreme12ft_rivershape_windconst_no_measures.toml",
    ]

    test_scenarios = {
        toml_file.name: Scenario.load_file(toml_file) for toml_file in test_tomls
    }
    return test_scenarios


# @pytest.mark.skip(reason="running the model takes long")
def test_hazard_preprocess_synthetic_wl(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()

    fn_bc = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_no_measures"
        / "Flooding"
        / "simulations"
        / "overland"
        / "sfincs.bzs"
    )
    wl = pd.read_csv(fn_bc, index_col=0, delim_whitespace=True, header=None)
    peak_model = wl.max().max()

    surge_peak = (
        test_scenario.direct_impacts.hazard.event.attrs.surge.shape_peak.convert(
            "meters"
        )
    )
    tide_amp = (
        test_scenario.direct_impacts.hazard.event.attrs.tide.harmonic_amplitude.convert(
            "meters"
        )
    )
    localdatum = test_scenario.site_info.attrs.water_level.localdatum.height.convert(
        "meters"
    ) - test_scenario.site_info.attrs.water_level.msl.height.convert("meters")

    slr_offset = test_scenario.site_info.attrs.slr.vertical_offset.convert("meters")

    assert np.abs(peak_model - (surge_peak + tide_amp + slr_offset - localdatum)) < 0.01


# @pytest.mark.skip(reason="There is no sfincs.inp checked in")
def test_hazard_preprocess_synthetic_discharge(test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()

    test_scenario.attrs.name = f"{test_scenario.attrs.name}_2"
    test_scenario.direct_impacts.hazard.name = f"{test_scenario.attrs.name}_2"
    test_scenario.direct_impacts.hazard.simulation_paths[0] = (
        test_scenario.direct_impacts.hazard.simulation_paths[0]
        .parents[1]
        .joinpath(
            f"{test_scenario.direct_impacts.hazard.simulation_paths[0].parents[0].name}_2",
            "overland",
        )
    )
    test_scenario.direct_impacts.hazard.site.attrs.river[0].x_coordinate += 100

    with pytest.raises(ValueError):
        test_scenario.direct_impacts.hazard.preprocess_models()


def test_preprocess_rainfall_timeseriesfile(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    event_path = test_db.input_path / "events" / "extreme12ft"

    test_scenario.init_object_model()

    hazard = test_scenario.direct_impacts.hazard
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


def test_preprocess_pump(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.attrs.strategy = "pump"
    test_scenario.attrs.name = test_scenario.attrs.name.replace("no_measures", "pump")
    test_scenario.init_object_model()

    hazard = test_scenario.direct_impacts.hazard

    hazard.preprocess_models()

    drn_file = hazard.simulation_paths[0].joinpath("sfincs.drn")
    assert drn_file.is_file()

    drn_templ = test_db.static_path / "templates" / "overland" / "sfincs.drn"

    ~filecmp.cmp(drn_file, drn_templ)


def test_preprocess_greenInfra(test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

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


def test_preprocess_greenInfra_aggr_area(test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.attrs.strategy = "total_storage_aggregation_area"
    test_scenario.init_object_model()
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy.measures[0],
        GreenInfrastructure,
    )
    test_scenario.direct_impacts.hazard.preprocess_models()


@pytest.mark.skip(reason="running the model takes long")
def test_write_floodmap_geotiff(test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()
    test_scenario.direct_impacts.hazard.postprocess_models()

    floodmap_fn = test_scenario.direct_impacts.hazard.simulation_paths[0].joinpath(
        "floodmap.tif"
    )
    assert floodmap_fn.is_file()


def test_preprocess_prob_eventset(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()

    bzs_file1 = (
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "simulations"
        / "event_0001"
        / "overland"
        / "sfincs.bzs"
    )
    bzs_file2 = (
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "simulations"
        / "event_0039"
        / "overland"
        / "sfincs.bzs"
    )
    assert bzs_file1.is_file()
    assert bzs_file2.is_file()
    assert ~filecmp.cmp(bzs_file1, bzs_file2)


def test_preprocess_rainfall_increase(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.attrs.name = "current_extreme12ft_precip_no_measures"
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.source = "shape"
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_type = "block"
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.cumulative = (
        UnitfulIntensity(value=5.0, units="inch/hr")
    )
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_start_time = -3
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_end_time = 3
    test_scenario.direct_impacts.hazard.preprocess_models()
    precip_file1 = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_precip_no_measures"
        / "Flooding"
        / "simulations"
        / "overland"
        / "sfincs.precip"
    )
    assert precip_file1.is_file()

    df1 = pd.read_csv(precip_file1, index_col=0, header=None, delim_whitespace=True)
    cum_precip1 = df1.sum()[1]

    test_scenario.attrs.name = "current_extreme12ft_precip_rainfall_incr_no_measures"
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.source = "shape"
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_type = "block"
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.cumulative = (
        UnitfulIntensity(value=5.0, units="inch/hr")
    )
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_start_time = -3
    test_scenario.direct_impacts.hazard.event.attrs.rainfall.shape_end_time = 3
    test_scenario.direct_impacts.hazard.physical_projection.attrs.rainfall_increase = (
        10  # in percent
    )
    test_scenario.direct_impacts.hazard.preprocess_models()

    precip_file2 = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_precip_rainfall_incr_no_measures"
        / "Flooding"
        / "simulations"
        / "overland"
        / "sfincs.precip"
    )
    assert precip_file2.is_file()
    df2 = pd.read_csv(precip_file2, index_col=0, header=None, delim_whitespace=True)
    cum_precip2 = df2.sum()[1]

    assert np.abs(cum_precip1 * 1.1 - cum_precip2) < 0.1


@pytest.mark.skip(reason="Running models takes a couple of minutes")
def test_run_prob_eventset(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()
    zs_file1 = (
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "simulations"
        / "event_0001"
        / "overland"
        / "sfincs_map.nc"
    )
    zs_file2 = (
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "simulations"
        / "event_0039"
        / "overland"
        / "sfincs_map.nc"
    )
    assert zs_file1.is_file()
    assert zs_file2.is_file()


@pytest.mark.skip(
    reason="Need to run models first (see above) but that takes a couple of minutes"
)
def test_rp_floodmap_calculation(test_db, test_scenarios):
    test_scenario = test_scenarios["current_test_set_no_measures.toml"]
    test_scenario.init_object_model()
    test_scenario.direct_impacts.hazard.calculate_rp_floodmaps()
    nc_file = (
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "rp_water_level.nc"
    )
    assert nc_file.is_file()
    zsrp = xr.open_dataset(nc_file).load()
    frequencies = test_scenario.direct_impacts.hazard.frequencies

    zs = []
    event_set = test_scenario.direct_impacts.hazard.event_set
    for ii, event in enumerate(event_set):
        zs_file = (
            test_db.output_path
            / "Scenarios"
            / "current_test_set_no_measures"
            / "Flooding"
            / "simulations"
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
        test_db.output_path
        / "Scenarios"
        / "current_test_set_no_measures"
        / "Flooding"
        / "simulations"
        / "floodmaps.png"
    )
    plt.savefig(fn, bbox_inches="tight", dpi=225)


def test_multiple_rivers(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()

    # Add an extra river
    test_scenario.direct_impacts.hazard.event.attrs.river.append(
        test_scenario.direct_impacts.hazard.event.attrs.river[0].copy()
    )
    # Overwrite river data of Event
    test_scenario.direct_impacts.hazard.event.attrs.river[0].source = "constant"
    test_scenario.direct_impacts.hazard.event.attrs.river[1].source = "shape"
    test_scenario.direct_impacts.hazard.event.attrs.river[
        0
    ].constant_discharge = UnitfulDischarge(value=2000.0, units="cfs")
    test_scenario.direct_impacts.hazard.event.attrs.river[1].shape_type = "gaussian"
    test_scenario.direct_impacts.hazard.event.attrs.river[
        1
    ].base_discharge = UnitfulDischarge(value=1000.0, units="cfs")
    test_scenario.direct_impacts.hazard.event.attrs.river[
        1
    ].shape_peak = UnitfulDischarge(value=2500.0, units="cfs")
    test_scenario.direct_impacts.hazard.event.attrs.river[1].shape_duration = 8
    test_scenario.direct_impacts.hazard.event.attrs.river[1].shape_peak_time = 0

    # Overwrite river data in Site
    name = test_scenario.site_info.attrs.river[0].name + "_test"
    description = test_scenario.site_info.attrs.river[0].description + " test"
    x = 596800.3
    y = 3672900.3
    mean_discharge = test_scenario.site_info.attrs.river[0].mean_discharge.value * 1.5

    # Add an extra river in site
    test_scenario.direct_impacts.hazard.site.attrs.river.append(
        test_scenario.direct_impacts.hazard.site.attrs.river[0].copy()
    )

    test_scenario.direct_impacts.hazard.site.attrs.river[1].name = name
    test_scenario.direct_impacts.hazard.site.attrs.river[1].x_coordinate = x
    test_scenario.direct_impacts.hazard.site.attrs.river[1].y_coordinate = y
    test_scenario.direct_impacts.hazard.site.attrs.river[
        1
    ].mean_discharge = UnitfulDischarge(value=mean_discharge, units="cfs")
    test_scenario.direct_impacts.hazard.site.attrs.river[1].description = description

    # Change name of reference model
    test_scenario.direct_impacts.hazard.site.attrs.sfincs.overland_model = (
        "overland_2_rivers"
    )

    # Preprocess the models
    test_scenario.direct_impacts.hazard.preprocess_models()

    # Check for the correct output
    output_folder = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_no_measures"
        / "Flooding"
        / "simulations"
        / "overland"
    )
    dis_file = output_folder / "sfincs.dis"
    src_file = output_folder / "sfincs.src"

    assert dis_file.is_file()
    assert src_file.is_file()

    # Check if content of file is correct
    dis = pd.read_csv(dis_file, index_col=0, header=None, delim_whitespace=True)

    assert len(dis.columns) == len(
        test_scenario.direct_impacts.hazard.event.attrs.river
    )
    assert round(
        np.mean(dis[1].values), 2
    ) == test_scenario.direct_impacts.hazard.event.attrs.river[
        0
    ].constant_discharge.convert(
        "m3/s"
    )
    assert np.max(
        dis[2].values
    ) == test_scenario.direct_impacts.hazard.event.attrs.river[1].shape_peak.convert(
        "m3/s"
    )


def test_no_rivers(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()

    # Overwrite river data of Event
    test_scenario.direct_impacts.hazard.event.attrs.river = []

    # Overwrite river data in Site
    test_scenario.direct_impacts.hazard.site.attrs.river = []

    # Change name of reference model
    test_scenario.direct_impacts.hazard.site.attrs.sfincs.overland_model = (
        "overland_0_rivers"
    )

    # Preprocess the models
    test_scenario.direct_impacts.hazard.preprocess_models()

    # Check for the correct output
    output_folder = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_no_measures"
        / "Flooding"
        / "simulations"
        / "overland"
    )
    dis_file = output_folder / "sfincs.dis"
    src_file = output_folder / "sfincs.src"
    bnd_file = output_folder / "sfincs.bnd"

    assert not dis_file.is_file()
    assert not src_file.is_file()
    assert bnd_file.is_file()  # To check if the model has run


def test_plot_wl_obs(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]
    test_scenario.init_object_model()

    # Preprocess the models
    test_scenario.direct_impacts.hazard.preprocess_models()
    test_scenario.direct_impacts.hazard.run_models()
    test_scenario.direct_impacts.hazard.plot_wl_obs()

    # Check for the correct output
    output_folder = (
        test_db.output_path
        / "Scenarios"
        / "current_extreme12ft_no_measures"
        / "Flooding"
    )
    html_file = output_folder / "8665530_timeseries.html"

    assert html_file.is_file()
