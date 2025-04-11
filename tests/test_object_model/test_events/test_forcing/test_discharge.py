from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.interface.models import REFERENCE_TIME, TimeFrame
from flood_adapt.object_model.hazard.interface.timeseries import (
    CSVTimeseries,
    ShapeType,
    TimeseriesFactory,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.io import unit_system as us


@pytest.fixture()
def river() -> RiverModel:
    return RiverModel(
        name="test_river",
        mean_discharge=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
        x_coordinate=0,
        y_coordinate=0,
    )


class TestDischargeConstant:
    def test_discharge_constant_to_dataframe(self, river):
        # Arrange
        _discharge = 100
        discharge = us.UnitfulDischarge(
            value=_discharge, units=us.UnitTypesDischarge.cms
        )

        # Act
        discharge_forcing = DischargeConstant(river=river, discharge=discharge)
        discharge_df = discharge_forcing.to_dataframe(time_frame=TimeFrame())

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        assert not discharge_df.empty
        assert len(discharge_df.columns) == 1
        assert discharge_df[river.name].max() == pytest.approx(_discharge, rel=1e-2)
        assert discharge_df[river.name].min() == pytest.approx(_discharge, rel=1e-2)


class TestDischargeSynthetic:
    def test_discharge_synthetic_to_dataframe(self, river):
        # Arrange
        start = REFERENCE_TIME
        duration = timedelta(hours=4)
        time_frame = TimeFrame(start_time=start, end_time=start + duration)

        timeseries = TimeseriesFactory.from_args(
            shape_type=ShapeType.block,
            duration=us.UnitfulTime(
                value=duration.total_seconds(), units=us.UnitTypesTime.seconds
            ),
            peak_time=us.UnitfulTime(
                value=duration.total_seconds() / 2, units=us.UnitTypesTime.seconds
            ),
            peak_value=us.UnitfulDischarge(value=2, units=us.UnitTypesDischarge.cms),
        )

        # Act
        discharge_forcing = DischargeSynthetic(river=river, timeseries=timeseries)
        discharge_df = discharge_forcing.to_dataframe(time_frame=time_frame)

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        assert not discharge_df.empty
        assert discharge_df.max().max() == pytest.approx(
            2.0, rel=1e-2
        ), f"{discharge_df.max()} != 2.0"
        assert discharge_df.min().min() == pytest.approx(
            2.0, rel=1e-2
        ), f"{discharge_df.min()} != 2.0"


class TestDischargeCSV:
    def test_discharge_from_csv_to_dataframe(
        self, tmp_path, dummy_1d_timeseries_df: pd.DataFrame, river
    ):
        # Arrange
        path = Path(tmp_path) / "test.csv"
        dummy_1d_timeseries_df.to_csv(path)
        time = TimeFrame(
            start_time=dummy_1d_timeseries_df.index[1],
            end_time=dummy_1d_timeseries_df.index[-2],
        )

        expected_df = CSVTimeseries.load_file(
            path=path,
            units=us.UnitfulDischarge(value=0, units=us.UnitTypesDischarge.cms),
        ).to_dataframe(time_frame=time)

        # Act
        discharge_df = DischargeCSV(river=river, path=path).to_dataframe(
            time_frame=time
        )

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        pd.testing.assert_frame_equal(discharge_df, expected_df)
