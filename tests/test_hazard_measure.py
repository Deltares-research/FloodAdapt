from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_floodwall_measure_from_toml():
    from flood_adapt.object_model.hazard.measure.floodwall import FloodWall

    test_toml = test_database / "charleston" / "input" / "measures" / "seawall" / "seawall.toml"
    assert test_toml.is_file()

    measure = FloodWall(test_toml)
    measure.load()
    
    assert measure.type == "floodwall"
    assert measure.elevation["value"] == 12
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.datum == "NAVD 88"

def test_floodwall_measure_without_datum_from_toml():
    from flood_adapt.object_model.hazard.measure.floodwall import FloodWall

    test_toml = test_database / "charleston" / "input" / "measures" / "seawall" / "seawall_without_datum.toml"
    assert test_toml.is_file()

    measure = FloodWall(test_toml)
    measure.load()
    
    assert measure.type == "floodwall"
    assert measure.elevation["value"] == 12
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.datum == None

    
