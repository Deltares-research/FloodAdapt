from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_read_config_slr():
    from flood_adapt.object_model.event_types.synthetic import Synthetic

    test_toml = test_database / "charleston" / "input" / "events" / "extreme12ft.toml"
    assert test_toml.is_file()

    test_synthetic = Synthetic(test_toml)

    assert test_synthetic
    assert isinstance(test_synthetic.config, dict)
