from datetime import datetime, timedelta

import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallMeteo,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.interface.models import Scstype
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.events import TimeModel
from flood_adapt.object_model.io import unit_system as us


class TestRainfallConstant:
    def test_rainfall_constant_get_data(self):
        # Arrange
        val = 10
        intensity = us.UnitfulIntensity(value=val, units=us.UnitTypesIntensity.mm_hr)

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
            duration=us.UnitfulTime(value=4, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
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
            duration=us.UnitfulTime(value=4, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            cumulative=us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
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
        start = datetime(2021, 1, 1, 0, 0, 0)
        duration = timedelta(hours=3)
        time = TimeModel(
            start_time=start,
            end_time=start + duration,
        )

        # Act
        wl_df = RainfallMeteo().get_data(t0=time.start_time, t1=time.end_time)

        # Assert
        assert isinstance(wl_df, xr.Dataset)
        # TODO more asserts
