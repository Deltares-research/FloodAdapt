from pathlib import Path

import pandas as pd
import pytest
from object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from object_model.interface.site import RiverModel
from object_model.io import unit_system as us


@pytest.fixture()
def river() -> RiverModel:
    return RiverModel(
        name="test_river",
        mean_discharge=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
        x_coordinate=0,
        y_coordinate=0,
    )


class TestDischargeConstant:
    def test_discharge_constant_get_data(self, river):
        # Arrange
        _discharge = 100
        discharge = us.UnitfulDischarge(
            value=_discharge, units=us.UnitTypesDischarge.cms
        )

        # Act
        discharge_df = DischargeConstant(river=river, discharge=discharge).get_data()

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        assert not discharge_df.empty
        assert len(discharge_df.columns) == 1
        assert discharge_df[river.name].max() == pytest.approx(_discharge, rel=1e-2)
        assert discharge_df[river.name].min() == pytest.approx(_discharge, rel=1e-2)


class TestDischargeSynthetic:
    def test_discharge_synthetic_get_data(self, river):
        # Arrange
        timeseries = SyntheticTimeseriesModel(
            shape_type=ShapeType.constant,
            duration=us.UnitfulTime(value=4, units=us.UnitTypesTime.hours),
            peak_time=us.UnitfulTime(value=2, units=us.UnitTypesTime.hours),
            peak_value=us.UnitfulLength(value=2, units=us.UnitTypesLength.meters),
        )

        # Act
        discharge_df = DischargeSynthetic(river=river, timeseries=timeseries).get_data()

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        assert not discharge_df.empty
        assert discharge_df.max().max() == pytest.approx(
            2, rel=1e-2
        ), f"{discharge_df.max()} != 2"
        assert discharge_df.min().min() == pytest.approx(
            2, rel=1e-2
        ), f"{discharge_df.min()} != 2"


class TestDischargeCSV:
    def test_discharge_from_csv_get_data(
        self, tmp_path, dummy_1d_timeseries_df: pd.DataFrame, river
    ):
        # Arrange
        path = Path(tmp_path) / "test.csv"
        dummy_1d_timeseries_df.to_csv(path)
        t0 = dummy_1d_timeseries_df.index[0]
        t1 = dummy_1d_timeseries_df.index[-1]

        # Act
        discharge_df = DischargeCSV(river=river, path=path).get_data(t0=t0, t1=t1)

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        pd.testing.assert_frame_equal(discharge_df, dummy_1d_timeseries_df)
