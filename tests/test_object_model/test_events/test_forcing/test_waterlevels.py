from unittest.mock import patch

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitfulTime


class TestWaterlevelSynthetic:
    @pytest.mark.parametrize(
        "surge_shape, peak_time, surge_duration, surge_peak_value, tide_amplitude, tide_period, tide_phase",
        [  # "surge_shape,       peak_time,                surge_duration,           surge_peak_value,           tide_amplitude,             tide_period,
            (
                ShapeType.gaussian,
                UnitfulTime(12, "hours"),
                UnitfulTime(24, "hours"),
                UnitfulLength(3, "meters"),
                UnitfulLength(1.5, "meters"),
                UnitfulTime(12, "hours"),
                UnitfulTime(8, "hours"),
            ),
            (
                ShapeType.gaussian,
                UnitfulTime(18, "hours"),
                UnitfulTime(36, "hours"),
                UnitfulLength(4, "meters"),
                UnitfulLength(2, "meters"),
                UnitfulTime(14, "hours"),
                UnitfulTime(6, "hours"),
            ),
            (
                ShapeType.gaussian,
                UnitfulTime(14, "hours"),
                UnitfulTime(28, "hours"),
                UnitfulLength(2, "meters"),
                UnitfulLength(0.8, "meters"),
                UnitfulTime(8, "hours"),
                UnitfulTime(4, "hours"),
            ),
            (
                ShapeType.constant,
                UnitfulTime(12, "hours"),
                UnitfulTime(12, "hours"),
                UnitfulLength(2, "meters"),
                UnitfulLength(1, "meters"),
                UnitfulTime(10, "hours"),
                UnitfulTime(4, "hours"),
            ),
            (
                ShapeType.constant,
                UnitfulTime(6, "hours"),
                UnitfulTime(6, "hours"),
                UnitfulLength(1, "meters"),
                UnitfulLength(0.5, "meters"),
                UnitfulTime(6, "hours"),
                UnitfulTime(2, "hours"),
            ),
            (
                ShapeType.constant,
                UnitfulTime(10, "hours"),
                UnitfulTime(20, "hours"),
                UnitfulLength(3, "meters"),
                UnitfulLength(1.2, "meters"),
                UnitfulTime(12, "hours"),
                UnitfulTime(6, "hours"),
            ),
            (
                ShapeType.triangle,
                UnitfulTime(12, "hours"),
                UnitfulTime(18, "hours"),
                UnitfulLength(1.5, "meters"),
                UnitfulLength(0.5, "meters"),
                UnitfulTime(8, "hours"),
                UnitfulTime(3, "hours"),
            ),
            (
                ShapeType.triangle,
                UnitfulTime(8, "hours"),
                UnitfulTime(16, "hours"),
                UnitfulLength(2.5, "meters"),
                UnitfulLength(1, "meters"),
                UnitfulTime(10, "hours"),
                UnitfulTime(5, "hours"),
            ),
            (
                ShapeType.triangle,
                UnitfulTime(16, "hours"),
                UnitfulTime(32, "hours"),
                UnitfulLength(3.5, "meters"),
                UnitfulLength(1.5, "meters"),
                UnitfulTime(10, "hours"),
                UnitfulTime(7, "hours"),
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


class TestWaterlevelFromCSV:
    # Arrange
    def test_waterlevel_from_csv_get_data(
        self, tmp_path, dummy_1d_timeseries_df: pd.DataFrame
    ):
        path = tmp_path / "test.csv"
        dummy_1d_timeseries_df.to_csv(path)
        t0 = dummy_1d_timeseries_df.index[0]
        t1 = dummy_1d_timeseries_df.index[-1]
        # Act
        wl_df = WaterlevelFromCSV(path=path).get_data(t0=t0, t1=t1)

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        pd.testing.assert_frame_equal(wl_df, dummy_1d_timeseries_df)


class TestWaterlevelFromModel:
    @patch("flood_adapt.integrator.sfincs_adapter.SfincsAdapter")
    def test_waterlevel_from_model_get_data(
        self, mock_sfincs_adapter, dummy_1d_timeseries_df, test_db: IDatabase, tmp_path
    ):
        # Arrange
        mock_instance = mock_sfincs_adapter.return_value
        mock_instance.__enter__.return_value = mock_instance
        mock_instance._get_wl_df_from_offshore_his_results.return_value = (
            dummy_1d_timeseries_df
        )

        test_path = tmp_path / "test_wl_from_model"

        # Act
        wl_df = WaterlevelFromModel(path=test_path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        pd.testing.assert_frame_equal(wl_df, dummy_1d_timeseries_df)


class TestWaterlevelFromGauged:
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
        wl_df = WaterlevelFromGauged(tide_gauge=test_db.site.attrs.tide_gauge).get_data(
            t0=t0, t1=t1
        )

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        pd.testing.assert_frame_equal(wl_df, dummy_1d_timeseries_df, check_names=False)
