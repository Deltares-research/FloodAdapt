from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_read_config_slr():
    from flood_adapt.object_model.risk_drivers.slr import SLR

    test_toml = test_database / "charleston" / "input" / "projections" / "all_projections" / "slr.toml"
    assert test_toml.is_file()

    test_slr = SLR(test_toml)

    assert test_slr
    assert isinstance(test_slr.config, dict)
