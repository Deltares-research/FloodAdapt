from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindFromMeteo,
)
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.models import (
    ForcingType,
    Mode,
    Template,
    TimeModel,
)
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulDischarge,
    UnitfulIntensity,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesVelocity,
)
from flood_adapt.object_model.scenario import Scenario


@pytest.fixture()
def setup_nearshore_event():
    event_attrs = {
        "name": "nearshore_gauged",
        "time": TimeModel(),
        "template": Template.Historical,
        "mode": Mode.single_event,
        "forcings": {
            "WATERLEVEL": WaterlevelFromGauged(),
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeConstant(
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
            ),
        },
    }
    return HistoricalEvent.load_dict(event_attrs)


@pytest.fixture()
def setup_offshore_meteo_event():
    event_attrs = {
        "name": "test_historical_offshore_meteo",
        "time": TimeModel(),
        "template": Template.Historical,
        "mode": Mode.single_event,
        "forcings": {
            "WATERLEVEL": WaterlevelFromModel(),
            "WIND": WindFromMeteo(),
            "RAINFALL": RainfallFromMeteo(),
            "DISCHARGE": DischargeConstant(
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
            ),
        },
    }
    return HistoricalEvent.load_dict(event_attrs)


@pytest.fixture()
def setup_offshore_scenario(
    setup_offshore_meteo_event: HistoricalEvent, test_db: IDatabase
):
    scenario_attrs = {
        "name": "test_scenario",
        "event": setup_offshore_meteo_event.attrs.name,
        "projection": "current",
        "strategy": "no_measures",
    }
    return Scenario.load_dict(scenario_attrs), setup_offshore_meteo_event


class TestHistoricalEvent:
    def test_save_event_toml(
        self, setup_offshore_meteo_event: HistoricalEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        event = setup_offshore_meteo_event
        event.save(path)
        assert path.exists()

    def test_load_file(
        self, setup_offshore_meteo_event: HistoricalEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        saved_event = setup_offshore_meteo_event
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        assert loaded_event == saved_event

    def test_process_sfincs_offshore(
        self, setup_offshore_scenario: tuple[Scenario, HistoricalEvent]
    ):
        # Arrange
        scenario, historical_event = setup_offshore_scenario
        undefined_path = historical_event.attrs.forcings[ForcingType.WATERLEVEL].path

        # Act
        historical_event.process(scenario)
        sim_path = historical_event.attrs.forcings[ForcingType.WATERLEVEL].path

        # Assert
        assert undefined_path is None
        assert sim_path.exists()

        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            wl_df = _offshore_model._get_wl_df_from_offshore_his_results()

        assert isinstance(wl_df, pd.DataFrame)
