from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import DataFrameContainer
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindCSV,
)


class TestWindConstant:
    def test_wind_constant_to_dataframe(self):
        # Arrange
        _speed = 10
        _dir = 90
        speed = us.UnitfulVelocity(value=_speed, units=us.UnitTypesVelocity.mps)
        direction = us.UnitfulDirection(value=_dir, units=us.UnitTypesDirection.degrees)

        # Act
        wind_df = WindConstant(speed=speed, direction=direction).to_dataframe(
            time_frame=TimeFrame()
        )

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
        assert wind_df["mag"].max() == _speed
        assert wind_df["dir"].min() == _dir


class TestWindMeteo:
    pass
    # Cant really test this class. Please look at MeteoHandler


class TestWindCSV:
    @pytest.fixture()
    def _create_dummy_csv(
        self, tmp_path: Path, dummy_2d_timeseries_df: pd.DataFrame
    ) -> Path:
        path = tmp_path / "wind.csv"
        dummy_2d_timeseries_df.columns = ["wind_u", "wind_v"]
        dummy_2d_timeseries_df.to_csv(path)
        return path

    def test_wind_from_csv_to_dataframe(self, _create_dummy_csv: Path):
        # Arrange
        path = _create_dummy_csv
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        ts = DataFrameContainer(name="wind", path=path)

        # Act
        wind_df = WindCSV(timeseries=ts).to_dataframe(time_frame=TimeFrame())

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty

    def test_wind_from_csv_save_additional(
        self, tmp_path: Path, _create_dummy_csv: Path
    ):
        # Arrange
        path = _create_dummy_csv
        ts = DataFrameContainer(name="wind", path=path)

        wind = WindCSV(timeseries=ts)
        expected_csv = tmp_path / "output" / "wind.csv"

        # Act
        wind.save_additional(output_dir=expected_csv.parent)

        # Assert
        assert expected_csv.exists()
