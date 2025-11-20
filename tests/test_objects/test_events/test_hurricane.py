import tempfile
from pathlib import Path

import pytest

from flood_adapt.objects.events.events import (
    ForcingType,
)
from flood_adapt.objects.events.hurricane import (
    HurricaneEvent,
)
from flood_adapt.objects.forcing.wind import WindTrack


class TestHurricaneEvent:
    def test_save_event_toml_and_track_file(
        self, setup_hurricane_event: HurricaneEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        event = setup_hurricane_event

        event.save(path)

        cyc_file = path.parent / f"{event.track_name}.cyc"
        assert path.exists()
        assert cyc_file.exists()

    def test_load_file(self, setup_hurricane_event: HurricaneEvent, tmp_path: Path):
        path = tmp_path / "test_event.toml"
        saved_event = setup_hurricane_event
        saved_event.save(path)
        cyc_file = path.parent / f"{saved_event.track_name}.cyc"
        assert path.exists()
        assert cyc_file.exists()

        loaded_event = HurricaneEvent.load_file(path)

        assert loaded_event == saved_event

    def test_load_file_raises_when_files_are_missing(
        self, setup_hurricane_event: HurricaneEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"

        saved_event = setup_hurricane_event
        saved_event.save(path)
        wind = saved_event.forcings[ForcingType.WIND][0]
        assert isinstance(wind, WindTrack)

        cyc_file = path.with_name(f"{wind.track.name}.cyc")

        assert path.exists()
        assert cyc_file.exists()

        cyc_file.unlink()

        with pytest.raises(
            FileNotFoundError, match=f"Failed to read Event. File {cyc_file.name}"
        ):
            HurricaneEvent.load_file(path)

    def test_save_additional_saves_cyc_file(
        self, setup_hurricane_event: HurricaneEvent
    ):
        # Arrange
        event = setup_hurricane_event
        toml_path = Path(tempfile.gettempdir()) / "test_event.toml"

        # Act
        event.save_additional(toml_path.parent)

        # Assert
        cyc_file = toml_path.parent / f"{event.track_name}.cyc"
        assert cyc_file.exists()
