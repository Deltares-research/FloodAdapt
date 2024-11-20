from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
)
from flood_adapt.object_model.hazard.interface.events import TimeModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesVelocity,
)


class TestWindConstant:
    def test_wind_constant_get_data(self):
        # Arrange
        _speed = 10
        _dir = 90
        speed = UnitfulVelocity(_speed, UnitTypesVelocity.mps)
        direction = UnitfulDirection(_dir, UnitTypesDirection.degrees)

        # Act
        wind_df = WindConstant(speed=speed, direction=direction).get_data()
        print(wind_df)
        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
        assert wind_df["data_0"].max() == _speed
        assert wind_df["data_1"].min() == _dir


class TestWindMeteo:
    def test_wind_from_meteo_get_data(self, test_db):
        # Arrange
        time = TimeModel(
            start_time=datetime.strptime("2021-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
            end_time=datetime.strptime("2021-01-01 00:10:00", "%Y-%m-%d %H:%M:%S"),
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
