from datetime import datetime

import object_model.io.unitfulvalue as uv
import pandas as pd
import pytest
import xarray as xr
from object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallSynthetic,
)
from object_model.hazard.interface.models import Scstype
from object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from object_model.interface.events import TimeModel


class TestRainfallConstant:
    def test_rainfall_constant_get_data(self):
        # Arrange
        val = 10
        intensity = uv.UnitfulIntensity(value=val, units=uv.UnitTypesIntensity.mm_hr)

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
            duration=uv.UnitfulTime(value=4, units=uv.UnitTypesTime.hours),
            peak_time=uv.UnitfulTime(value=2, units=uv.UnitTypesTime.hours),
            peak_value=uv.UnitfulLength(value=2, units=uv.UnitTypesLength.meters),
        )

        # Act
        rf_df = RainfallSynthetic(timeseries=timeseries).get_data()

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
        assert rf_df.max().max() == pytest.approx(2, rel=1e-2), f"{rf_df.max()} != 2"
        assert rf_df.min().min() == pytest.approx(2, rel=1e-2), f"{rf_df.min()} != 2"

    def test_rainfall_synthetic_scs_get_data(self):
        # Arrange
        timeseries = SyntheticTimeseriesModel(
            shape_type=ShapeType.scs,
            duration=uv.UnitfulTime(value=4, units=uv.UnitTypesTime.hours),
            peak_time=uv.UnitfulTime(value=2, units=uv.UnitTypesTime.hours),
            cumulative=uv.UnitfulLength(value=2, units=uv.UnitTypesLength.meters),
            scs_file_name="scs_rainfall.csv",
            scs_type=Scstype.type1,
        )

        # Act
        rf_df = RainfallSynthetic(timeseries=timeseries).get_data()

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty


class TestRainfallMeteo:
    def test_rainfall_from_meteo_get_data(self, test_db):
        # Arrange
        time = TimeModel(
            start_time=datetime.strptime("2021-01-01 00:00:00", "%Y-%m-%d %H:%M:%S"),
            end_time=datetime.strptime("2021-01-02 00:00:00", "%Y-%m-%d %H:%M:%S"),
        )

        # Act
        wl_df = RainfallMeteo().get_data(t0=time.start_time, t1=time.end_time)

        # Assert
        assert isinstance(wl_df, xr.Dataset)
        # TODO more asserts