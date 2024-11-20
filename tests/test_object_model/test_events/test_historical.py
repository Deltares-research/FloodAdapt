import tempfile
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeFromCSV,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
)
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromCSV,
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
from flood_adapt.object_model.interface.site import RiverModel
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
def setup_nearshore_event(dummy_1d_timeseries_df: pd.DataFrame):
    def _tmp_timeseries_csv(name: str):
        tmp_csv = Path(tempfile.gettempdir()) / name
        dummy_1d_timeseries_df.to_csv(tmp_csv)
        return Path(tmp_csv)

    event_attrs = {
        "name": "nearshore_gauged",
        "time": TimeModel(),
        "template": Template.Historical,
        "mode": Mode.single_event,
        "forcings": {
            "WATERLEVEL": WaterlevelFromCSV(path=_tmp_timeseries_csv("waterlevel.csv")),
            "WIND": WindConstant(
                speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                direction=UnitfulDirection(value=60, units=UnitTypesDirection.degrees),
            ),
            "RAINFALL": RainfallConstant(
                intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
            ),
            "DISCHARGE": DischargeFromCSV(
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=UnitfulDischarge(
                        value=5000, units=UnitTypesDischarge.cfs
                    ),
                ),
                path=_tmp_timeseries_csv("discharge.csv"),
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
                river=RiverModel(
                    name="cooper",
                    description="Cooper River",
                    x_coordinate=595546.3,
                    y_coordinate=3675590.6,
                    mean_discharge=UnitfulDischarge(
                        value=5000, units=UnitTypesDischarge.cfs
                    ),
                ),
                discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs),
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

    def test_save_additional_csv(
        self, setup_nearshore_event: HistoricalEvent, tmp_path: Path
    ):
        # Arrange
        path = tmp_path / "test_event.toml"
        event = setup_nearshore_event
        expected_csvs = [
            path.parent / "waterlevel.csv",
            path.parent / "discharge.csv",
        ]

        # Act
        event.save_additional(output_dir=path.parent)

        # Assert
        assert all(csv.exists() for csv in expected_csvs)

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
            wl_df = _offshore_model.get_wl_df_from_offshore_his_results()

        assert isinstance(wl_df, pd.DataFrame)
