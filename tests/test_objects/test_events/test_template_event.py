import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.config.hazard import RiverModel
from flood_adapt.misc.io import read_toml
from flood_adapt.objects.events.historical import HistoricalEvent
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import DischargeConstant
from flood_adapt.objects.forcing.forcing import ForcingSource, ForcingType
from flood_adapt.objects.forcing.rainfall import (
    RainfallCSV,
)
from flood_adapt.objects.forcing.time_frame import (
    TimeFrame,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelCSV,
)
from flood_adapt.objects.forcing.wind import (
    WindCSV,
)


@pytest.fixture()
def _wind_csv(dummy_2d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "wind.csv"
    dummy_2d_timeseries_df.to_csv(tmp_path)

    return WindCSV(
        path=tmp_path,
    )


@pytest.fixture()
def _rainfall_csv(dummy_1d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "rainfall.csv"
    dummy_1d_timeseries_df.to_csv(tmp_path)

    return RainfallCSV(
        path=tmp_path,
    )


@pytest.fixture()
def _waterlevel_csv(dummy_1d_timeseries_df: pd.DataFrame):
    tmp_path = Path(tempfile.gettempdir()) / "waterlevel.csv"
    dummy_1d_timeseries_df.to_csv(tmp_path)

    return WaterlevelCSV(
        path=tmp_path,
    )


@pytest.fixture()
def test_event_all_csv(_wind_csv, _rainfall_csv, _waterlevel_csv):
    return HistoricalEvent(
        name="test_synthetic_nearshore",
        time=TimeFrame(
            start_time=datetime(2020, 1, 1),
            end_time=datetime(2020, 1, 2),
        ),
        forcings={
            ForcingType.WIND: [
                _wind_csv,
            ],
            ForcingType.RAINFALL: [
                _rainfall_csv,
            ],
            ForcingType.DISCHARGE: [
                DischargeConstant(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    discharge=us.UnitfulDischarge(
                        value=5000, units=us.UnitTypesDischarge.cfs
                    ),
                )
            ],
            ForcingType.WATERLEVEL: [
                _waterlevel_csv,
            ],
        },
    )


class TestHistoricalEvent:
    def test_save_event_toml_and_datafiles(
        self, test_event_all_csv: HistoricalEvent, tmp_path
    ):
        path = tmp_path / "test_event.toml"
        test_event = test_event_all_csv
        test_event.save(path)
        assert path.exists()
        content = read_toml(path)
        loaded_event = HistoricalEvent.load_file(path)
        csv_forcings = [
            f for f in loaded_event.get_forcings() if f.source == ForcingSource.CSV
        ]
        for forcing in csv_forcings:
            assert forcing.path.exists()
            assert (
                forcing.path == path.parent / forcing.path.name
            ), "Expected forcing path to be updated to new location."
            assert (
                forcing.path.name == content["forcings"][forcing.type][0]["path"]
            ), "Expected forcing path to be saved as just the file name in toml file."

    def test_load_event_toml_and_datafiles(self, test_event_all_csv, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = test_event_all_csv
        test_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        csv_forcings = [
            f for f in loaded_event.get_forcings() if f.source == ForcingSource.CSV
        ]
        for forcing in csv_forcings:
            assert forcing.path.exists()
            assert (
                forcing.path == path.parent / forcing.path.name
            ), "Expected forcing path to be absolute. Constructed from the filename saved in the toml, and the parent dir of the toml file."

    def test_load_file(self, test_event_all_csv, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = test_event_all_csv
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path)

        assert loaded_event == saved_event
