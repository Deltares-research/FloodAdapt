import shutil

import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
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
            wl_df["values"].max() <= expected_max
        ), f"Expected max {surge_peak_value} + {tide_amplitude} ~ {expected_max}, got {wl_df['values'].max()}"
        assert (
            wl_df["values"].min() >= expected_min
        ), f"Expected min {-abs(tide_amplitude.value)} ~ {expected_min}, got {wl_df['values'].min()}"


class TestWaterlevelFromCSV:
    def test_waterlevel_from_csv_get_data(self, tmp_path):
        # Arrange
        data = {
            "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
            "values": [1, 2],
        }
        df = pd.DataFrame(data)
        df = df.set_index("time")
        path = tmp_path / "test.csv"
        df.to_csv(path)

        # Act
        wl_df = WaterlevelFromCSV(path=path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert wl_df["values"].max() == pytest.approx(2, rel=1e-2)
        assert wl_df["values"].min() == pytest.approx(1, rel=1e-2)
        assert len(wl_df["values"]) == 2
        assert len(wl_df.index) == 2


class TestWaterlevelFromModel:
    def test_waterlevel_from_model_get_data(self, test_db: IDatabase, tmp_path):
        # Arrange
        offshore_template = test_db.static_path / "templates" / "offshore"
        test_path = tmp_path / "test_wl_from_model"

        if test_path.exists():
            shutil.rmtree(test_path)
        shutil.copytree(offshore_template, test_path)

        with SfincsAdapter(model_root=test_path, database=test_db) as offshore_model:
            offshore_model.write(test_path)
            offshore_model.execute()

        # Act
        wl_df = WaterlevelFromModel(path=test_path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        # TODO more asserts?


class TestWaterlevelFromGauged:
    def test_waterlevel_from_gauge_get_data(self, test_db: IDatabase, tmp_path):
        # Arrange
        data = {
            "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
            "values": [1, 2],
        }
        df = pd.DataFrame(data)
        df = df.set_index("time")

        path = tmp_path / "test.csv"
        df.to_csv(path)

        # Act
        wl_df = WaterlevelFromGauged(path=path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert wl_df["values"].max() == pytest.approx(2, rel=1e-2)
        assert wl_df["values"].min() == pytest.approx(1, rel=1e-2)
        assert len(wl_df["values"]) == 2
        assert len(wl_df.index) == 2
