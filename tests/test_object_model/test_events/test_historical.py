from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallConstant
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindConstant
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.timeseries import CSVTimeseries
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


class TestHistoricalEvent:
    @pytest.fixture()
    def test_event_all_constant_no_waterlevels(self):
        attrs = {
            "name": "test_historical_nearshore",
            "time": TimeModel(),
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
    def test_event_no_waterlevels(
        self, test_event_all_constant_no_waterlevels: dict[str, Any]
    ):
        return HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)

    @pytest.fixture()
    def test_scenario(self, test_db, test_event_no_waterlevels: HistoricalEvent):
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

    @pytest.fixture()
    def setup_gauged_scenario(
        self,
        test_db: IDatabase,
        test_event_no_waterlevels: HistoricalEvent,
        dummy_1d_timeseries_df: pd.DataFrame,
        tmp_path: Path,
    ) -> tuple[IDatabase, Scenario, HistoricalEvent, Mock, pd.DataFrame, Path, Path]:
        with patch(
            "flood_adapt.object_model.hazard.event.tide_gauge.TideGauge"
        ) as mock_tide_gauge:
            gauged_event = test_event_no_waterlevels
            mock_tide_gauge._cached_data = {}
            path = tmp_path / "gauge_data.csv"
            dummy_1d_timeseries_df.to_csv(path)

            expected_df = CSVTimeseries.load_file(path).to_dataframe(
                start_time=gauged_event.attrs.time.start_time,
                end_time=gauged_event.attrs.time.end_time,
            )

            obj = mock_tide_gauge.return_value
            obj._read_imported_waterlevels.return_value = expected_df
            obj._download_tide_gauge_data.return_value = expected_df
            obj.attrs.path = path

            gauged_event.attrs.forcings[ForcingType.WATERLEVEL] = WaterlevelFromGauged()

            test_db.events.save(gauged_event)
            gauged_scn = Scenario.load_dict(
                {
                    "name": "test_scenario",
                    "event": gauged_event.attrs.name,
                    "projection": "current",
                    "strategy": "no_measures",
                }
            )
            expected_path = (
                test_db.events.get_database_path() / gauged_event.attrs.name / path.name
            )

            return (
                test_db,
                gauged_scn,
                gauged_event,
                mock_tide_gauge,
                expected_df,
                path,
                expected_path,
            )

    @pytest.fixture()
    def mock_unused_methods_for_gauged(self):
        mocked_functions = [
            "flood_adapt.object_model.hazard.event.meteo.download_meteo",
            "flood_adapt.object_model.hazard.event.meteo.read_meteo",
            "flood_adapt.object_model.hazard.event.historical.HistoricalEvent._preprocess_sfincs_offshore",
            "flood_adapt.object_model.hazard.event.historical.HistoricalEvent._run_sfincs_offshore",
        ]

        patches = [patch(mock) for mock in mocked_functions]

        yield [p.start() for p in patches]

        for p in patches:
            p.stop()

    def test_save_event_toml(
        self, test_event_all_constant_no_waterlevels: dict[str, Any], tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        test_event = HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)
        test_event.save(path)
        assert path.exists()

    def test_load_dict(self, test_event_all_constant_no_waterlevels: dict[str, Any]):
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

    def test_load_file(
        self, test_event_all_constant_no_waterlevels: dict[str, Any], tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        saved_event = HistoricalEvent.load_dict(test_event_all_constant_no_waterlevels)
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        assert loaded_event == saved_event

    def test_process_without_waterlevels_should_call_nothing(
        self,
        test_scenario: Scenario,
        test_event_no_waterlevels: HistoricalEvent,
        mock_unused_methods_for_gauged: tuple[Mock, Mock, Mock, Mock],
    ):
        # Arrange
        event = test_event_no_waterlevels

        # Act
        event.process(test_scenario)

        # Assert
        for mock in mock_unused_methods_for_gauged:
            mock.assert_not_called()

    def test_process_gauged(
        self,
        setup_gauged_scenario: tuple[
            IDatabase, Scenario, HistoricalEvent, Mock, pd.DataFrame, Path, Path
        ],
        mock_unused_methods_for_gauged: tuple[Mock, Mock, Mock, Mock],
    ):
        # Arrange
        (
            test_db,
            test_scenario,
            test_event,
            mock_tide_gauge,
            expected_df,
            path,
            expected_path,
        ) = setup_gauged_scenario

        # Act
        test_event.process(test_scenario)
        result_df = test_event.attrs.forcings[ForcingType.WATERLEVEL].get_data(
            t0=test_event.attrs.time.start_time, t1=test_event.attrs.time.end_time
        )

        # Assert
        for mock in mock_unused_methods_for_gauged:
            mock.assert_not_called()

        assert expected_path.exists()
        print(result_df, expected_df, sep="\n\n")
        pd.testing.assert_frame_equal(expected_df, result_df)
