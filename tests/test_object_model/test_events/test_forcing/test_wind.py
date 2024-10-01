import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
import xarray as xr

from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindFromCSV,
    WindFromMeteo,
)
from flood_adapt.object_model.hazard.event.meteo import download_meteo
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


class TestWindFromMeteo:
    def test_wind_from_meteo_get_data(self, tmp_path, test_db):
        # Arrange
        test_path = tmp_path / "test_wl_from_meteo"

        if test_path.exists():
            shutil.rmtree(test_path)

        time = TimeModel(
            start_time=datetime.strptime("2021-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
            end_time=datetime.strptime("2021-01-01 00:10:00", "%Y-%m-%d %H:%M:%S"),
        )
        download_meteo(
            time=time,
            meteo_dir=test_path,
            site=test_db.site.attrs,
        )

        # Act
        wind_df = WindFromMeteo(path=test_path).get_data()

        # Assert
        assert isinstance(wind_df, xr.Dataset)
        # TODO more asserts


class TestWindFromCSV:
    def test_wind_from_csv_get_data(
        self, tmp_path, dummy_2d_timeseries_df: pd.DataFrame
    ):
        # Arrange
        path = Path(tmp_path) / "wind/test.csv"
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
        # Required coordinates: ['time', 'y', 'x']

        dummy_2d_timeseries_df.columns = ["wind_u", "wind_v"]
        dummy_2d_timeseries_df.to_csv(path)

        # Act
        wind_df = WindFromCSV(path=path).get_data()

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
