import shutil

import pandas as pd
import pytest

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    SurgeModel,
    TideModel,
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.interface.timeseries import (
    ShapeType,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitfulTime


class TestWaterlevelSynthetic:
    def test_waterlevel_synthetic_get_data(self):
        # Arrange
        surge_model = SurgeModel(
            timeseries=SyntheticTimeseriesModel(
                shape_type=ShapeType.constant,
                duration=UnitfulTime(4, "hours"),
                peak_time=UnitfulTime(2, "hours"),
                peak_value=UnitfulLength(2, "meters"),
            )
        )

        tide_model = TideModel(
            harmonic_amplitude=UnitfulLength(1, "meters"),
            harmonic_period=UnitfulTime(4, "hours"),
            harmonic_phase=UnitfulTime(2, "hours"),
        )

        # Act
        wl_df = WaterlevelSynthetic(surge=surge_model, tide=tide_model).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert wl_df["values"].max() == pytest.approx(3, rel=1e-2)
        assert wl_df["values"].min() == pytest.approx(1, rel=1e-2)


class TestWaterlevelFromCSV:
    def test_waterlevel_from_csv_get_data(self, tmp_path):
        # Arrange
        data = {
            "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
            "values": [1, 2],
        }
        df = pd.DataFrame(data)
        df = df.set_index("time")
        path = tmp_path / "test.csv"
        df.to_csv(path)

        # Act
        wl_df = WaterlevelFromCSV(path=path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert wl_df["values"].max() == pytest.approx(2, rel=1e-2)
        assert wl_df["values"].min() == pytest.approx(1, rel=1e-2)
        assert len(wl_df["values"]) == 2
        assert len(wl_df.index) == 2


class TestWaterlevelFromModel:
    def test_waterlevel_from_model_get_data(self, test_db: IDatabase, tmp_path):
        # Arrange
        offshore_template = test_db.static_path / "templates" / "offshore"
        test_path = tmp_path / "test_wl_from_model"

        if test_path.exists():
            shutil.rmtree(test_path)
        shutil.copytree(offshore_template, test_path)

        with SfincsAdapter(model_root=test_path, database=test_db) as offshore_model:
            offshore_model.write(test_path)
            offshore_model.execute()

        # Act
        wl_df = WaterlevelFromModel(path=test_path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        # TODO more asserts?


class TestWaterlevelFromGauged:
    def test_waterlevel_from_gauge_get_data(self, test_db: IDatabase, tmp_path):
        # Arrange
        data = {
            "time": ["2021-01-01 00:00:00", "2021-01-01 01:00:00"],
            "values": [1, 2],
        }
        df = pd.DataFrame(data)
        df = df.set_index("time")

        path = tmp_path / "test.csv"
        df.to_csv(path)

        # Act
        wl_df = WaterlevelFromGauged(path=path).get_data()

        # Assert
        assert isinstance(wl_df, pd.DataFrame)
        assert not wl_df.empty
        assert wl_df["values"].max() == pytest.approx(2, rel=1e-2)
        assert wl_df["values"].min() == pytest.approx(1, rel=1e-2)
        assert len(wl_df["values"]) == 2
        assert len(wl_df.index) == 2
