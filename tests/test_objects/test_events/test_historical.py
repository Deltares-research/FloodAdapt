from datetime import timedelta
from pathlib import Path

import pandas as pd
import pytest

from flood_adapt.config.hazard import RiverModel
from flood_adapt.objects.events.historical import (
    HistoricalEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import (
    DischargeCSV,
)
from flood_adapt.objects.forcing.forcing import ForcingType
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
)
from flood_adapt.objects.forcing.time_frame import (
    REFERENCE_TIME,
    TimeFrame,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelCSV,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
)


@pytest.fixture()
def setup_nearshore_event(tmp_path: Path, dummy_1d_timeseries_df: pd.DataFrame):
    def _tmp_timeseries_csv(name: str):
        tmp_csv = tmp_path / name
        dummy_1d_timeseries_df.to_csv(tmp_csv)
        return tmp_csv

    time = TimeFrame(
        start_time=REFERENCE_TIME, end_time=REFERENCE_TIME + timedelta(hours=2)
    )

    return HistoricalEvent(
        name="nearshore_gauged",
        time=time,
        forcings={
            ForcingType.WATERLEVEL: [
                WaterlevelCSV(path=_tmp_timeseries_csv("waterlevel.csv"))
            ],
            ForcingType.WIND: [
                WindConstant(
                    speed=us.UnitfulVelocity(value=5, units=us.UnitTypesVelocity.mps),
                    direction=us.UnitfulDirection(
                        value=60, units=us.UnitTypesDirection.degrees
                    ),
                )
            ],
            ForcingType.RAINFALL: [
                RainfallConstant(
                    intensity=us.UnitfulIntensity(
                        value=20, units=us.UnitTypesIntensity.mm_hr
                    )
                )
            ],
            ForcingType.DISCHARGE: [
                DischargeCSV(
                    river=RiverModel(
                        name="cooper",
                        description="Cooper River",
                        x_coordinate=595546.3,
                        y_coordinate=3675590.6,
                        mean_discharge=us.UnitfulDischarge(
                            value=5000, units=us.UnitTypesDischarge.cfs
                        ),
                    ),
                    path=_tmp_timeseries_csv("discharge.csv"),
                ),
            ],
        },
    )


def test_save_additional_csv(setup_nearshore_event: HistoricalEvent, tmp_path: Path):
    # Arrange
    path = tmp_path / "test_event.toml"
    event = setup_nearshore_event
    expected_csvs = [
        path.parent / "waterlevel.csv",
        path.parent / "discharge.csv",
    ]

    # Act
    event.save(toml_path=path)

    # Assert
    assert all(csv.exists() for csv in expected_csvs)


def test_save_and_load(setup_nearshore_event: HistoricalEvent, tmp_path: Path):
    path = tmp_path / "test_event.toml"
    saved_event = setup_nearshore_event
    saved_event.save(path)
    assert path.exists()

    loaded_event = HistoricalEvent.load_file(path)

    assert loaded_event == saved_event
