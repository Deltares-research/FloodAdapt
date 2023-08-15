from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.events import RainfallModel, TideModel
from flood_adapt.object_model.interface.site import SCSModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site

test_database = Path().absolute() / "tests" / "test_database"


def test_scenario_class():
    scenario_toml = (
        test_database
        / "charleston"
        / "input"
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml"
    )
    assert scenario_toml.is_file()

    scenario = Scenario.load_file(scenario_toml)
    scenario.init_object_model()

    assert isinstance(scenario.site_info, Site)
    assert isinstance(scenario.direct_impacts, DirectImpacts)
    assert isinstance(
        scenario.direct_impacts.socio_economic_change, SocioEconomicChange
    )
    assert isinstance(scenario.direct_impacts.impact_strategy, ImpactStrategy)
    assert isinstance(scenario.direct_impacts.hazard, Hazard)
    assert isinstance(scenario.direct_impacts.hazard.hazard_strategy, HazardStrategy)
    assert isinstance(
        scenario.direct_impacts.hazard.physical_projection, PhysicalProjection
    )
    assert isinstance(scenario.direct_impacts.hazard.event_list[0], Synthetic)


def test_hazard_load():
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

    hazard = scenario.direct_impacts.hazard

    assert hazard.event_list[0].attrs.timing == "idealized"
    assert isinstance(hazard.event_list[0].attrs.tide, TideModel)


def test_hazard_wl():
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

    hazard = scenario.direct_impacts.hazard

    hazard.add_wl_ts()

    assert isinstance(hazard.wl_ts, pd.DataFrame)
    assert len(hazard.wl_ts) > 1
    assert isinstance(hazard.wl_ts.index, pd.DatetimeIndex)


@pytest.mark.skip(
    reason="Test csv file is missing and bug in the code according to team"
)
def test_scs_rainfall():
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

    hazard = scenario.direct_impacts.hazard

    hazard.event.attrs.rainfall = RainfallModel(
        source="shape",
        cumulative=UnitfulLength(value=10.0, units="inch"),
        shape_type="scs",
        shape_start_time=-24,
        shape_duration=10,
    )
    hazard.site.attrs.scs = SCSModel(
        file="scs_rainfall.csv",
        type="type_3",
    )

    scsfile = hazard.database_input_path.parent.joinpath(
        "static", "scs", hazard.site.attrs.scs.file
    )
    scstype = hazard.site.attrs.scs.type
    hazard.event.add_rainfall_ts(scsfile=scsfile, scstype=scstype)
    assert isinstance(hazard.event.rain_ts, pd.DataFrame)
    assert isinstance(hazard.event.rain_ts.index, pd.DatetimeIndex)
    hazard.event.rain_ts.to_csv(
        (test_database / "charleston" / "input" / "events" / "extreme12ft" / "rain.csv")
    )
    cum_rainfall_ts = (
        np.trapz(
            hazard.event.rain_ts.to_numpy().squeeze(),
            hazard.event.rain_ts.index.to_numpy().astype(float),
        )
        / 3.6e12
    )
    cum_rainfall_toml = hazard.event.attrs.rainfall.cumulative.convert("millimeters")
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


@pytest.mark.skip(reason="No metric file to read from")
def test_infographic():
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
    test_scenario.infographic()


@pytest.mark.skip(reason="We cannot depend on the P drive")
def test_run_hazard_model():
    test_toml = (
        Path(
            r"p:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/database/charleston/input"
        )
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml"
    )

    assert test_toml.is_file()

    scenario = Scenario.load_file(test_toml)

    scenario.run_hazard_models()

    df = pd.read_csv(
        Path(
            r"p:/11207949-dhs-phaseii-floodadapt/FloodAdapt/Test_data/database/charleston/output"
        )
        / "simulations"
        / "current_extreme12ft_no_measures"
        / "overland"
        / "sfincs.bzs",
    )

    assert df.iloc[0, 0][-4:] == "0.86"


@pytest.mark.skip(reason="wind not implemented yet")
def test_wind_constant():
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

    hazard = scenario.direct_impacts.hazard

    hazard.add_wind_ts()

    assert isinstance(hazard.event_obj.wind_ts, pd.DataFrame)
    assert len(hazard.event_obj.wind_ts) > 1
    assert isinstance(hazard.event_obj.wind_ts.index, pd.DatetimeIndex)
