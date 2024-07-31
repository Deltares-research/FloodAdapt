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
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.meteo import download_meteo
from flood_adapt.object_model.hazard.interface.events import Mode, Template, TimeModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDirection,
    UnitfulVelocity,
    UnitTypesDirection,
    UnitTypesVelocity,
)


class TestWindConstant:
    def test_wind_constant_get_data(self):
        # Arrange
        speed = UnitfulVelocity(10, UnitTypesVelocity.mps)
        direction = UnitfulDirection(90, UnitTypesDirection.degrees)

        # Act
        wind_df = WindConstant(speed=speed, direction=direction).get_data()

        # Assert
        assert wind_df is None


class TestWindFromMeteo:
    def test_wind_from_model_get_data(self, tmp_path, test_db):
        # Arrange
        test_path = tmp_path / "test_wl_from_model"

        if test_path.exists():
            shutil.rmtree(test_path)

        time = TimeModel(
            start_time=datetime.strptime(
                "2021-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"
            ),
            end_time=datetime.strptime("2021-01-01 00:10:00", "%Y-%m-%d %H:%M:%S"),
        )
        site = test_db.site.attrs

        download_meteo(
            time=time,
            meteo_dir=test_path,
            site=site,
        )

        # Act
        wind_df = WindFromMeteo(path=test_path).get_data()

        # Assert
        assert isinstance(wind_df, xr.Dataset)

        # TODO more asserts


class TestWindFromCSV:
    def test_wind_from_csv_get_data(self, tmp_path):
        # Arrange
        path = Path(tmp_path) / "wind/test.csv"
        if not path.parent.exists():
            path.parent.mkdir(parents=True)

        # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
        # Required coordinates: ['time', 'y', 'x']

        data = pd.DataFrame(
            {
                "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
                "wind_u": [1, 2],
                "wind_v": [2, 3],
            }
        )
        data.to_csv(path)

        # Act
        wind_df = WindFromCSV(path=path).get_data()

        # Assert
        assert isinstance(wind_df, pd.DataFrame)
        assert not wind_df.empty
