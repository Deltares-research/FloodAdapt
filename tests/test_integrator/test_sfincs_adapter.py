from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.scenario import Scenario

test_database = Path().absolute() / "tests" / "test_database"


def test_add_obs_points(cleanup_database: None):
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
    scenario.init_object_model()
    path_in = test_database.joinpath(
        "charleston",
        "static",
        "templates",
        scenario.site_info.attrs.sfincs.overland_model,
    )

    model = SfincsAdapter(site=scenario.site_info, model_root=path_in)

    model.add_obs_points()

    # write sfincs model in output destination
    model.write_sfincs_model(
        path_out=scenario.direct_impacts.hazard.simulation_paths[0]
    )

    del model

    # assert points are the same
    sfincs_obs = pd.read_csv(
        scenario.direct_impacts.hazard.simulation_paths[0].joinpath("sfincs.obs"),
        header=None,
        delim_whitespace=True,
    )

    names = [scenario.site_info.attrs.obs_station.name]
    lat = [scenario.site_info.attrs.obs_station.lat]
    lon = [scenario.site_info.attrs.obs_station.lon]

    site_points = scenario.site_info.attrs.obs_point
    for pt in site_points:
        names.append(pt.name)
        lat.append(pt.lat)
        lon.append(pt.lon)
    df = pd.DataFrame({"Name": names, "Latitude": lat, "Longitude": lon})
    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df.Longitude, df.Latitude), crs="EPSG:4326"
    )
    site_obs = gdf.drop(columns=["Longitude", "Latitude"]).to_crs(epsg=26917)

    assert np.abs(sfincs_obs.loc[0, 0] - site_obs.loc[0].geometry.x) < 1
    assert np.abs(sfincs_obs.loc[0, 1] - site_obs.loc[0].geometry.y) < 1
    assert np.abs(sfincs_obs.loc[1, 0] - site_obs.loc[1].geometry.x) < 1
    assert np.abs(sfincs_obs.loc[1, 1] - site_obs.loc[1].geometry.y) < 1

    # test when no obs_station is provided
    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()
    site = scenario.site_info
    site.attrs.obs_station = None
    model = SfincsAdapter(site=scenario.site_info, model_root=path_in)

    model.add_obs_points()

    # write sfincs model in output destination
    model.write_sfincs_model(
        path_out=scenario.direct_impacts.hazard.simulation_paths[0]
    )
    del model

    sfincs_obs = pd.read_csv(
        scenario.direct_impacts.hazard.simulation_paths[0].joinpath("sfincs.obs"),
        header=None,
        delim_whitespace=True,
    )

    assert np.abs(sfincs_obs.loc[0, 0] - site_obs.loc[1].geometry.x) < 1
    assert np.abs(sfincs_obs.loc[0, 1] - site_obs.loc[1].geometry.y) < 1

    # test when no obs_point is provided
    scenario = Scenario.load_file(test_toml)
    scenario.init_object_model()
    site = scenario.site_info
    site.attrs.obs_point = None
    model = SfincsAdapter(site=scenario.site_info, model_root=path_in)

    model.add_obs_points()

    # write sfincs model in output destination
    model.write_sfincs_model(
        path_out=scenario.direct_impacts.hazard.simulation_paths[0]
    )
    del model

    sfincs_obs = pd.read_csv(
        scenario.direct_impacts.hazard.simulation_paths[0].joinpath("sfincs.obs"),
        header=None,
        delim_whitespace=True,
    )

    assert np.abs(sfincs_obs.loc[0, 0] - site_obs.loc[0].geometry.x) < 1
    assert np.abs(sfincs_obs.loc[0, 1] - site_obs.loc[0].geometry.y) < 1
