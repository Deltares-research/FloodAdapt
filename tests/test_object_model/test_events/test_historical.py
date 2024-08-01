from datetime import datetime
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
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


class TestHistoricalEvent:
    @pytest.fixture()
    def test_event_all_constant_no_waterlevels(self):
        attrs = {
            "name": "test_historical_nearshore",
            "time": TimeModel(
                start_time=datetime(2020, 1, 1),
                end_time=datetime(2020, 1, 2),
            ),
            "template": Template.Historical,
            "mode": Mode.single_event,
            "forcings": {
                "WIND": WindConstant(
                    speed=UnitfulVelocity(value=5, units=UnitTypesVelocity.mps),
                    direction=UnitfulDirection(
                        value=60, units=UnitTypesDirection.degrees
                    ),
                ),
                "RAINFALL": RainfallConstant(
                    intensity=UnitfulIntensity(value=20, units=UnitTypesIntensity.mm_hr)
                ),
                "DISCHARGE": DischargeConstant(
                    discharge=UnitfulDischarge(value=5000, units=UnitTypesDischarge.cfs)
                ),
            },
        }
        return attrs

    @pytest.fixture()
    def test_event_no_waterlevels(self, test_event_all_constant_no_waterlevels):
        return HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)

    @pytest.fixture()
    def test_scenario(self, test_db, test_event_no_waterlevels):
        test_db.events.save(test_event_no_waterlevels)
        scn = Scenario.load_dict(
            {
                "name": "test_scenario",
                "event": test_event_no_waterlevels.attrs.name,
                "projection": "current",
                "strategy": "no_measures",
            }
        )
        return scn

    def test_save_event_toml(self, test_event_all_constant_no_waterlevels, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)
        test_event.save(path)
        assert path.exists()

    def test_load_dict(self, test_event_all_constant_no_waterlevels):
        loaded_event = HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)

        assert loaded_event.attrs.name == test_event_all_constant_no_waterlevels["name"]
        assert loaded_event.attrs.time == test_event_all_constant_no_waterlevels["time"]
        assert (
            loaded_event.attrs.template
            == test_event_all_constant_no_waterlevels["template"]
        )
        assert loaded_event.attrs.mode == test_event_all_constant_no_waterlevels["mode"]
        assert (
            loaded_event.attrs.forcings
            == test_event_all_constant_no_waterlevels["forcings"]
        )

    def test_load_file(self, test_event_all_constant_no_waterlevels, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        assert loaded_event == saved_event

    def test_process_without_offshore_run(
        self, tmp_path, test_scenario, test_event_no_waterlevels
    ):
        # Arrange
        event: HistoricalEvent = test_event_no_waterlevels
        path = Path(tmp_path) / "gauge_data.csv"
        time = pd.date_range(
            start=event.attrs.time.start_time,
            end=event.attrs.time.end_time,
            freq=event.attrs.time.time_step,
        )
        data = pd.DataFrame(
            index=time,
            data={
                "value": range(len(time)),
            },
        )
        data.to_csv(path)
        test_event_no_waterlevels.attrs.forcings["WATERLEVEL"] = WaterlevelFromGauged(
            path=path
        )

        # Mocking
        event.download_meteo = mock.Mock()
        event.read_meteo = mock.Mock()
        event._preprocess_sfincs_offshore = mock.Mock()
        event._run_sfincs_offshore = mock.Mock()
        event._process_single_event = mock.Mock()

        # Act
        event.process(test_scenario)

        # Assert
        event.download_meteo.assert_not_called()
        event.read_meteo.assert_not_called()
        event._preprocess_sfincs_offshore.assert_not_called()
        event._run_sfincs_offshore.assert_not_called()

        event._process_single_event.assert_called_once()
