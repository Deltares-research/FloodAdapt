from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeFromCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulLength,
    UnitfulTime,
    UnitTypesDischarge,
)


class TestDischargeConstant:
    def test_discharge_constant_get_data(self):
        # Arrange
        discharge = UnitfulDischarge(100, UnitTypesDischarge.cms)

        # Act
        discharge_df = DischargeConstant(discharge=discharge).get_data()

        # Assert
        assert discharge_df is None


class TestDischargeSynthetic:
    def test_discharge_synthetic_get_data(self):
        # Arrange
        timeseries = SyntheticTimeseriesModel(
            shape_type=ShapeType.constant,
            duration=UnitfulTime(4, "hours"),
            peak_time=UnitfulTime(2, "hours"),
            peak_value=UnitfulLength(2, "meters"),
        )

        # Act
        discharge_df = DischargeSynthetic(timeseries=timeseries).get_data()

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
    def test_discharge_from_csv_get_data(self, tmp_path):
        # Arrange
        data = {
            "time": [
                "2021-01-01 00:00:00",
                "2021-01-01 00:10:00",
                "2021-01-01 00:20:00",
                "2021-01-01 00:30:00",
                "2021-01-01 00:40:00",
            ],
            "discharge": [1, 2, 3, 2, 1],
        }
        df = pd.DataFrame(data)
        df = df.set_index("time")
        path = Path(tmp_path) / "test.csv"
        df.to_csv(path)

        # Act
        discharge_df = DischargeFromCSV(path=path).get_data()

        # Assert
        assert isinstance(discharge_df, pd.DataFrame)
        assert not discharge_df.empty
        assert discharge_df.max().max() == pytest.approx(3, rel=1e-2)
        assert discharge_df.min().min() == pytest.approx(1, rel=1e-2)
