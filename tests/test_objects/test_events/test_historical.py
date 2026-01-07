from pathlib import Path

from flood_adapt.objects.events.historical import (
    HistoricalEvent,
)


class TestHistoricalEvent:
    def test_save_event_toml(
        self, setup_nearshore_event: HistoricalEvent, tmp_path: Path
    ):
        path = tmp_path / "test_event.toml"
        event = setup_nearshore_event
        event.save(path)
        assert path.exists()

    def test_save_additional_csv(
        self, setup_nearshore_event: HistoricalEvent, tmp_path: Path
    ):
        # Arrange
        path = tmp_path / "test_event.toml"
        event = setup_nearshore_event
        expected_csvs = [
            path.parent / "waterlevel.csv",
            path.parent / "cooper.csv",
        ]

        # Act
        event.save_additional(output_dir=path.parent)

        # Assert
        assert all(csv.exists() for csv in expected_csvs)

    def test_load_file(self, setup_nearshore_event: HistoricalEvent, tmp_path: Path):
        path = tmp_path / "test_event.toml"
        saved_event = setup_nearshore_event
        saved_event.save(path)
        assert path.exists()

        loaded_event = HistoricalEvent.load_file(path, load_all=True)

        assert loaded_event == saved_event
