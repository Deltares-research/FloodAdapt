import shutil
from datetime import datetime

import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.event.meteo import download_meteo
from flood_adapt.object_model.hazard.interface.events import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulIntensity,
    UnitfulLength,
    UnitfulTime,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesTime,
)


class TestRainfallConstant:
    def test_rainfall_constant_get_data(self):
        # Arrange
        val = 10
        intensity = UnitfulIntensity(value=val, units=UnitTypesIntensity.mm_hr)

        # Act
        rf_df = RainfallConstant(intensity=intensity).get_data()

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
        assert rf_df.max().max() == pytest.approx(val, rel=1e-2)
        assert rf_df.min().min() == pytest.approx(val, rel=1e-2)


class TestRainfallSynthetic:
    def test_rainfall_synthetic_get_data(self):
        # Arrange
        timeseries = SyntheticTimeseriesModel(
            shape_type=ShapeType.constant,
            duration=UnitfulTime(value=4, units=UnitTypesTime.hours),
            peak_time=UnitfulTime(value=2, units=UnitTypesTime.hours),
            peak_value=UnitfulLength(value=2, units=UnitTypesLength.meters),
        )

        # Act
        rf_df = RainfallSynthetic(timeseries=timeseries).get_data()

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
        assert rf_df.max().max() == pytest.approx(2, rel=1e-2), f"{rf_df.max()} != 2"
        assert rf_df.min().min() == pytest.approx(2, rel=1e-2), f"{rf_df.min()} != 2"


class TestRainfallFromMeteo:
    def test_rainfall_from_meteo_get_data(self, test_db, tmp_path):
        # Arrange
        test_path = tmp_path / "test_rainfall_from_meteo"

        if test_path.exists():
            shutil.rmtree(test_path)

        time = TimeModel(
            start_time=datetime.strptime("2021-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
            end_time=datetime.strptime("2021-01-02 00:00:00", "%Y-%m-%d %H:%M:%S"),
        )
        download_meteo(meteo_dir=test_path, time=time, site=test_db.site.attrs)

        # Act
        wl_df = RainfallFromMeteo(path=test_path).get_data()

        # Assert
        assert isinstance(wl_df, xr.DataArray)
        # TODO more asserts
