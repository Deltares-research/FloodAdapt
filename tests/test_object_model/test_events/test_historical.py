import tempfile
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
)
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelModel,
)
from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindMeteo,
)
from flood_adapt.object_model.hazard.interface.events import (
    Mode,
    Template,
)
from flood_adapt.object_model.hazard.interface.models import (
    TimeModel,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io import unit_system as us
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
            "WATERLEVEL": WaterlevelCSV(path=_tmp_timeseries_csv("waterlevel.csv")),
            "WIND": WindConstant(
                speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                direction=us.UnitfulDirection(
                    value=60, units=us.UnitTypesDirection.degrees
                ),
            ),
            "RAINFALL": RainfallConstant(
                intensity=us.UnitfulIntensity(
                    value=20, units=us.UnitTypesIntensity.mm_hr
                )
            ),
            "DISCHARGE": {
                "cooper": DischargeCSV(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    path=_tmp_timeseries_csv("discharge.csv"),
                ),
            },
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
            "WATERLEVEL": WaterlevelModel(),
            "WIND": WindMeteo(),
            "RAINFALL": RainfallMeteo(),
            "DISCHARGE": {
                "cooper": DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                ),
            },
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