from flood_adapt.objects.events.synthetic import (
    SyntheticEvent,
)


class TestSyntheticEvent:
    # TODO add test for for eventmodel validators
    def test_save_event_toml(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        test_event = test_event_all_synthetic
        test_event.save(path)
        assert path.exists()

    def test_load_file(self, test_event_all_synthetic, tmp_path):
        path = tmp_path / "test_event.toml"
        saved_event = test_event_all_synthetic
        saved_event.save(path)
        assert path.exists()

        loaded_event = SyntheticEvent.load_file(path)

        assert loaded_event == saved_event
