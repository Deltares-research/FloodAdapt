import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.scenario import Scenario


@pytest.fixture()
def test_scenarios(test_db):
    test_tomls = [
        test_db.input_path
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    ]

    test_scenarios = {
        toml_file.name: Scenario.load_file(toml_file) for toml_file in test_tomls
    }
    return test_scenarios


def test_add_obs_points(test_db, test_scenarios):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.init_object_model()
    path_in = (
        test_db.static_path
        / "templates"
        / test_scenario.site_info.attrs.sfincs.overland_model
    )

    model = SfincsAdapter(site=test_scenario.site_info, model_root=path_in)

    model.add_obs_points()

    # write sfincs model in output destination
    model.write_sfincs_model(
        path_out=test_scenario.direct_impacts.hazard.simulation_paths[0]
    )

    del model

    # assert points are the same
    sfincs_obs = pd.read_csv(
        test_scenario.direct_impacts.hazard.simulation_paths[0].joinpath("sfincs.obs"),
        header=None,
        delim_whitespace=True,
    )

    names = []
    lat = []
    lon = []

    site_points = test_scenario.site_info.attrs.obs_point
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
