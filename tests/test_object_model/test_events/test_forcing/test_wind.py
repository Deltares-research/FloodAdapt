from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
)
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io import unit_system as us


class TestWindConstant:
    def test_wind_constant_get_data(self):
        # Arrange
        _speed = 10
        _dir = 90
        speed = us.UnitfulVelocity(_speed, us.UnitTypesVelocity.mps)
        direction = us.UnitfulDirection(_dir, us.UnitTypesDirection.degrees)

        # Act
        wind_df = WindConstant(speed=speed, direction=direction).get_data()

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
        assert wind_df["data_0"].max() == _speed
        assert wind_df["data_1"].min() == _dir


class TestWindMeteo:
    def test_wind_from_meteo_get_data(self, test_db):
        # Arrange
        start = datetime(2021, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)
        time = TimeModel(
            start_time=start,
            end_time=start + duration,
        )

        # Act
        wind_df = WindMeteo().get_data(t0=time.start_time, t1=time.end_time)

        # Assert
        assert isinstance(wind_df, xr.Dataset)
        # TODO more asserts


class TestWindCSV:
    @pytest.fixture()
    def _create_dummy_csv(
        self, tmp_path: Path, dummy_2d_timeseries_df: pd.DataFrame
    ) -> Path:
        path = tmp_path / "wind.csv"
        dummy_2d_timeseries_df.columns = ["wind_u", "wind_v"]
        dummy_2d_timeseries_df.to_csv(path)
        return path

    def test_wind_from_csv_get_data(self, _create_dummy_csv: Path):
        # Arrange
        path = _create_dummy_csv
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        # Act
        wind_df = WindCSV(path=path).get_data()

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty

    def test_wind_from_csv_save_additional(
        self, tmp_path: Path, _create_dummy_csv: Path
    ):
        # Arrange
        path = _create_dummy_csv

        wind = WindCSV(path=path)
        expected_csv = tmp_path / "output" / "wind.csv"

        # Act
        wind.save_additional(output_dir=expected_csv.parent)

        # Assert
        assert expected_csv.exists()
