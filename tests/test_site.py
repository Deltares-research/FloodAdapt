from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_read_site_toml():
    from flood_adapt.object_model.site import SiteConfig

    test_toml = test_database / "charleston" / "static" / "site" / "charleston_vs2.toml"
    assert test_toml.is_file()

    test_data = SiteConfig(config_path=test_toml)

    assert test_data
    assert isinstance(test_data.name, str)
    assert isinstance(test_data.long_name, str)
    assert isinstance(test_data.lat, float)
    assert isinstance(test_data.lon, float)
    assert isinstance(test_data.sfincs, dict)
    assert isinstance(test_data.slr, dict)
    assert isinstance(test_data.risk, dict)
    assert isinstance(test_data.gui, dict)
    assert isinstance(test_data.dem, dict)
    assert isinstance(test_data.fiat, dict)