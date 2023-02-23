from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_floodwall_measure_from_toml():
    from flood_adapt.object_model.hazard.measure_tdw.floodwall import FloodWall

    test_toml = test_database / "charleston" / "input" / "measures" / "seawall" / "seawall.toml"
    assert test_toml.is_file()

    measure = FloodWall()
    measure.load(test_toml)
    
    assert measure.name == "seawall"
    assert measure.long_name == "seawall"
    assert measure.type == "floodwall"
    assert measure.elevation["value"] == 12
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"