from unittest.mock import patch

import pandas as pd
import pytest

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.hazard.event.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallMeteo
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindMeteo
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.site import RiverModel
from flood_adapt.object_model.io import unit_system as us
from flood_adapt.object_model.scenario import Scenario


class TestWaterlevelSynthetic:
    @pytest.mark.parametrize(
        "surge_shape, peak_time, surge_duration, surge_peak_value, tide_amplitude, tide_period, tide_phase",
        [  # "surge_shape,       peak_time,                surge_duration,           surge_peak_value,           tide_amplitude,             tide_period,
            (
                ShapeType.gaussian,
                us.UnitfulTime(12, "hours"),
                us.UnitfulTime(24, "hours"),
                us.UnitfulLength(3, "meters"),
                us.UnitfulLength(1.5, "meters"),
                us.UnitfulTime(12, "hours"),
                us.UnitfulTime(8, "hours"),
            ),
            (
                ShapeType.gaussian,
                us.UnitfulTime(18, "hours"),
                us.UnitfulTime(36, "hours"),
                us.UnitfulLength(4, "meters"),
                us.UnitfulLength(2, "meters"),
                us.UnitfulTime(14, "hours"),
                us.UnitfulTime(6, "hours"),
            ),
            (
                ShapeType.gaussian,
                us.UnitfulTime(14, "hours"),
                us.UnitfulTime(28, "hours"),
                us.UnitfulLength(2, "meters"),
                us.UnitfulLength(0.8, "meters"),
                us.UnitfulTime(8, "hours"),
                us.UnitfulTime(4, "hours"),
            ),
            (
                ShapeType.constant,
                us.UnitfulTime(12, "hours"),
                us.UnitfulTime(12, "hours"),
                us.UnitfulLength(2, "meters"),
                us.UnitfulLength(1, "meters"),
                us.UnitfulTime(10, "hours"),
                us.UnitfulTime(4, "hours"),
            ),
            (
                ShapeType.constant,
                us.UnitfulTime(6, "hours"),
                us.UnitfulTime(6, "hours"),
                us.UnitfulLength(1, "meters"),
                us.UnitfulLength(0.5, "meters"),
                us.UnitfulTime(6, "hours"),
                us.UnitfulTime(2, "hours"),
            ),
            (
                ShapeType.constant,
                us.UnitfulTime(10, "hours"),
                us.UnitfulTime(20, "hours"),
                us.UnitfulLength(3, "meters"),
                us.UnitfulLength(1.2, "meters"),
                us.UnitfulTime(12, "hours"),
                us.UnitfulTime(6, "hours"),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(12, "hours"),
                us.UnitfulTime(18, "hours"),
                us.UnitfulLength(1.5, "meters"),
                us.UnitfulLength(0.5, "meters"),
                us.UnitfulTime(8, "hours"),
                us.UnitfulTime(3, "hours"),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(8, "hours"),
                us.UnitfulTime(16, "hours"),
                us.UnitfulLength(2.5, "meters"),
                us.UnitfulLength(1, "meters"),
                us.UnitfulTime(10, "hours"),
                us.UnitfulTime(5, "hours"),
            ),
            (
                ShapeType.triangle,
                us.UnitfulTime(16, "hours"),
                us.UnitfulTime(32, "hours"),
                us.UnitfulLength(3.5, "meters"),
                us.UnitfulLength(1.5, "meters"),
                us.UnitfulTime(10, "hours"),
                us.UnitfulTime(7, "hours"),
            ),
        ],
    )
    def test_waterlevel_synthetic_get_data(
        self,
        peak_time,
        surge_shape,
        surge_duration,
        surge_peak_value,
        tide_amplitude,
        tide_period,
        tide_phase,
    ):
        # Arrange
        surge_model = SurgeModel(
            timeseries=SyntheticTimeseriesModel(
                shape_type=surge_shape,
                duration=surge_duration,
                peak_time=peak_time,
                peak_value=surge_peak_value,
            )
        )

        tide_model = TideModel(
            harmonic_amplitude=tide_amplitude,
            harmonic_period=tide_period,
            harmonic_phase=tide_phase,
        )

        expected_max = abs((surge_peak_value + tide_amplitude).value)
        expected_min = -abs(tide_amplitude.value)

        # Act
        wl_df = WaterlevelSynthetic(surge=surge_model, tide=tide_model).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert (
            wl_df["data_0"].max() <= expected_max
        ), f"Expected max {surge_peak_value} + {tide_amplitude} ~ {expected_max}, got {wl_df['data_0'].max()}"
        assert (
            wl_df["data_0"].min() >= expected_min
        ), f"Expected min {-abs(tide_amplitude.value)} ~ {expected_min}, got {wl_df['data_0'].min()}"


class TestWaterlevelCSV:
    # Arrange
    def test_waterlevel_from_csv_get_data(
        self, tmp_path, dummy_1d_timeseries_df: pd.DataFrame
    ):
        path = tmp_path / "test.csv"
        dummy_1d_timeseries_df.to_csv(path)
        t0 = dummy_1d_timeseries_df.index[0]
        t1 = dummy_1d_timeseries_df.index[-1]
        # Act
        wl_df = WaterlevelCSV(path=path).get_data(t0=t0, t1=t1)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        pd.testing.assert_frame_equal(wl_df, dummy_1d_timeseries_df)


class TestWaterlevelModel:
    @pytest.fixture()
    def setup_offshore_scenario(self, test_db: IDatabase):
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

        event = HistoricalEvent.load_dict(event_attrs)
        test_db.events.save(event)

        scenario_attrs = {
            "name": "test_scenario",
            "event": event.attrs.name,
            "projection": "current",
            "strategy": "no_measures",
        }
        scn = Scenario.load_dict(scenario_attrs)
        test_db.scenarios.save(scn)

        return test_db, scn, event

    def test_process_sfincs_offshore(
        self, setup_offshore_scenario: tuple[IDatabase, Scenario, HistoricalEvent]
    ):
        # Arrange
        _, scenario, _ = setup_offshore_scenario

        # Act
        wl_df = WaterlevelModel().get_data(scenario=scenario)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)

    def test_waterlevel_from_model_get_data(self, setup_offshore_scenario):
        # Arrange
        _, scenario, _ = setup_offshore_scenario

        # Act
        wl_df = WaterlevelModel().get_data(scenario=scenario)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)


class TestWaterlevelGauged:
    @pytest.fixture()
    def mock_tide_gauge(self, dummy_1d_timeseries_df: pd.DataFrame):
        with patch(
            "flood_adapt.object_model.hazard.event.forcing.waterlevels.TideGauge.get_waterlevels_in_time_frame"
        ) as mock_download_wl:
            mock_download_wl.return_value = dummy_1d_timeseries_df
            yield mock_download_wl, dummy_1d_timeseries_df

    def test_waterlevel_from_gauge_get_data(self, test_db: IDatabase, mock_tide_gauge):
        # Arrange
        _, dummy_1d_timeseries_df = mock_tide_gauge
        t0 = dummy_1d_timeseries_df.index[0]
        t1 = dummy_1d_timeseries_df.index[-1]

        # Act
        wl_df = WaterlevelGauged(tide_gauge=test_db.site.attrs.tide_gauge).get_data(
            t0=t0, t1=t1
        )

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        pd.testing.assert_frame_equal(wl_df, dummy_1d_timeseries_df, check_names=False)
