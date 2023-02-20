from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_read_config():
    from flood_adapt.object_model.io.config_io import read_config
    print(test_database)
    test_toml = test_database / "charleston\input\events\extreme12ft\extreme12ft.toml"
    print(test_toml)
    config = read_config(test_toml)

    assert config
    assert isinstance(config, dict)

