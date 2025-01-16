from datetime import timedelta

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallConstant,
    RainfallSynthetic,
)
from flood_adapt.object_model.hazard.interface.forcing import Scstype
from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io import unit_system as us


class TestRainfallConstant:
    def test_rainfall_constant_to_dataframe(self):
        # Arrange
        val = 10
        intensity = us.UnitfulIntensity(value=val, units=us.UnitTypesIntensity.mm_hr)

        # Act
        rainfall_forcing = RainfallConstant(intensity=intensity)
        rf_df = rainfall_forcing.to_dataframe(time_frame=TimeModel())

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
        assert rf_df.max().max() == pytest.approx(val, rel=1e-2)
        assert rf_df.min().min() == pytest.approx(val, rel=1e-2)


class TestRainfallSynthetic:
    def test_rainfall_synthetic_to_dataframe(self):
        # Arrange
        start = pd.Timestamp("2020-01-01")
        duration = timedelta(hours=4)

        time_frame = TimeModel(
            start_time=start,
            end_time=start + duration,
        )

        timeseries = SyntheticTimeseriesModel(
            shape_type=ShapeType.block,
            duration=us.UnitfulTime(
                value=duration.total_seconds(), units=us.UnitTypesTime.seconds
            ),
            peak_time=us.UnitfulTime(
                value=duration.total_seconds() / 2, units=us.UnitTypesTime.seconds
            ),
            peak_value=us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
        )

        # Act
        rainfall_forcing = RainfallSynthetic(timeseries=timeseries)
        rf_df = rainfall_forcing.to_dataframe(time_frame=time_frame)

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
        assert rf_df.max().max() == pytest.approx(
            2.0, rel=1e-2
        ), f"{rf_df.max()} != 2.0"
        assert rf_df.min().min() == pytest.approx(
            2.0, rel=1e-2
        ), f"{rf_df.min()} != 2.0"

    def test_rainfall_synthetic_scs_to_dataframe(self):
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
        rainfall_forcing = RainfallSynthetic(timeseries=timeseries)
        rf_df = rainfall_forcing.to_dataframe(time_frame=TimeModel())

        # Assert
        assert isinstance(rf_df, pd.DataFrame)
        assert not rf_df.empty
