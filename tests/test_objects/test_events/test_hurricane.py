from pathlib import Path

import pytest

from flood_adapt.config.hazard import RiverModel
from flood_adapt.objects.events.events import (
    ForcingType,
)
from flood_adapt.objects.events.hurricane import (
    HurricaneEvent,
)
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.forcing.discharge import DischargeConstant
from flood_adapt.objects.forcing.rainfall import RainfallTrack
from flood_adapt.objects.forcing.time_frame import (
    TimeFrame,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelModel,
)
from flood_adapt.objects.forcing.wind import WindTrack
from tests.fixtures import TEST_DATA_DIR


@pytest.fixture()
def setup_hurricane_event() -> tuple[HurricaneEvent, Path]:
    cyc_file = TEST_DATA_DIR / "IAN.cyc"
    event = HurricaneEvent(
        name="hurricane",
        time=TimeFrame(),
        track_name="IAN",
        forcings={
            ForcingType.WATERLEVEL: [WaterlevelModel()],
            ForcingType.WIND: [WindTrack(path=cyc_file)],
            ForcingType.RAINFALL: [RainfallTrack(path=cyc_file)],
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
                ),
            ],
        },
    )
    return event


def test_save_and_load(setup_hurricane_event: HurricaneEvent, tmp_path: Path):
    path = tmp_path / "test_event.toml"
    event = setup_hurricane_event

    event.save(path)

    cyc_file = path.parent / f"{event.track_name}.cyc"
    assert path.exists()
    assert cyc_file.exists()

    loaded_event = HurricaneEvent.load_file(path)
    assert loaded_event == event


def test_load_file_raises_when_files_are_missing(
    setup_hurricane_event: HurricaneEvent, tmp_path: Path
):
    path = tmp_path / "test_event.toml"
    setup_hurricane_event.save(path)

    loaded = HurricaneEvent.load_file(path)

    wind = loaded.forcings[ForcingType.WIND][0]
    assert isinstance(wind, WindTrack)
    assert path.exists()
    assert wind.path.exists()

    wind.path.unlink()
    with pytest.raises(FileNotFoundError) as e:
        HurricaneEvent.load_file(path)

    assert f"File {wind.path} does not exist" in str(e.value)
