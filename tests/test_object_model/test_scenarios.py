import numpy as np
import pandas as pd
import pytest

from flood_adapt.integrator.direct_impacts_integrator import DirectImpacts
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection

# from flood_adapt.object_model.interface.events import RainfallModel, TideModel
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.site import SCSModel
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site


@pytest.fixture(autouse=True)
def test_tomls(test_db) -> list:
    toml_files = [
        test_db.input_path
        / "scenarios"
        / "all_projections_extreme12ft_strategy_comb"
        / "all_projections_extreme12ft_strategy_comb.toml",
        test_db.input_path
        / "scenarios"
        / "current_extreme12ft_no_measures"
        / "current_extreme12ft_no_measures.toml",
    ]
    yield toml_files


@pytest.fixture(autouse=True)
def test_scenarios(test_db, test_tomls) -> dict[str, Scenario]:
    test_scenarios = {
        toml_file.name: Scenario.load_file(toml_file) for toml_file in test_tomls
    }
    yield test_scenarios


def test_initObjectModel_validInput(test_db, test_scenarios):
    test_scenario = test_scenarios["all_projections_extreme12ft_strategy_comb.toml"]

    test_scenario.init_object_model()

    assert isinstance(test_scenario.site_info, Site)
    assert isinstance(test_scenario.direct_impacts, DirectImpacts)
    assert isinstance(
        test_scenario.direct_impacts.socio_economic_change, SocioEconomicChange
    )
    assert isinstance(test_scenario.direct_impacts.impact_strategy, ImpactStrategy)
    assert isinstance(test_scenario.direct_impacts.hazard, FloodMap)
    assert isinstance(
        test_scenario.direct_impacts.hazard.hazard_strategy, HazardStrategy
    )
    assert isinstance(
        test_scenario.direct_impacts.hazard.physical_projection, PhysicalProjection
    )


@pytest.mark.skip(reason="Refactor to use the new event model")
def test_scs_rainfall(test_db: IDatabase, test_scenarios: dict[str, Scenario]):
    test_scenario = test_scenarios["current_extreme12ft_no_measures.toml"]

    test_scenario.init_object_model()

    # event = test_db.events.get(test_scenario.direct_impacts.hazard.event_name)

    # event.attrs.rainfall = RainfallModel(
    #     source="shape",
    #     cumulative=UnitfulLength(value=10.0, units="inch"),
    #     shape_type="scs",
    #     shape_start_time=-24,
    #     shape_duration=10,
    # )

    hazard = test_scenario.direct_impacts.hazard
    hazard.site.attrs.scs = SCSModel(
        file="scs_rainfall.csv",
        type="type_3",
    )

    scsfile = test_db.static_path / "scs" / test_db.site.attrs.scs.file
    scstype = test_db.site.attrs.scs.type

    # event = test_db.events.get(test_scenario.direct_impacts.hazard.event_name)
    hazard.event.add_rainfall_ts(scsfile=scsfile, scstype=scstype)

    assert isinstance(hazard.event.rain_ts, pd.DataFrame)
    assert isinstance(hazard.event.rain_ts.index, pd.DatetimeIndex)
    cum_rainfall_ts = (
        np.trapz(
            hazard.event.rain_ts.to_numpy().squeeze(),
            hazard.event.rain_ts.index.to_numpy().astype(float),
        )
        / 3.6e12
    )
    cum_rainfall_toml = hazard.event.attrs.rainfall.cumulative.value
    assert np.abs(cum_rainfall_ts - cum_rainfall_toml) < 0.01


class Test_scenario_run:
    @pytest.fixture(scope="class")
    def test_scenario_before_after_run(self, test_db_class: IDatabase):
        before_run_name = "current_extreme12ft_no_measures"
        after_run_name = "current_extreme12ft_no_measures_run"

        test_db_class.scenarios.copy(
            old_name=before_run_name,
            new_name=after_run_name,
            new_description="temp_description",
        )

        after_run = test_db_class.scenarios.get(after_run_name)
        after_run.run()

        yield test_db_class, before_run_name, after_run_name

    def test_run_change_has_run(self, test_scenario_before_after_run):
        test_db, before_run, after_run = test_scenario_before_after_run
        before_run = test_db.scenarios.get(before_run)
        after_run = test_db.scenarios.get(after_run)

        assert not before_run.direct_impacts.hazard.has_run
        assert after_run.direct_impacts.hazard.has_run

    @pytest.mark.skip(reason="Refactor/move test")
    def test_infographic(self, test_db):
        test_toml = (
            test_db.input_path
            / "scenarios"
            / "current_extreme12ft_no_measures"
            / "current_extreme12ft_no_measures.toml"
        )

        assert test_toml.is_file()

        # use event template to get the associated Event child class
        test_scenario = Scenario.load_file(test_toml)
        test_scenario.init_object_model()
        test_scenario.infographic()
