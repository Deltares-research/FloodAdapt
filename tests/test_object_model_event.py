from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_read_config_synthetic():
    from flood_adapt.object_model.hazard.event.synthetic import Synthetic

    test_toml = test_database / "charleston" / "input" / "events" / "extreme12ft" / "extreme12ft.toml"
    assert test_toml.is_file()

    test_synthetic = Synthetic(test_toml)
    test_synthetic.load()

    assert test_synthetic
    assert isinstance(test_synthetic.config, dict)
