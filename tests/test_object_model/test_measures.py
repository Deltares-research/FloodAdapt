from pathlib import Path

test_database = Path().absolute() / 'tests' / 'test_database'

def test_floodwall_measure_from_toml():
    from flood_adapt.object_model.hazard.measure.floodwall import FloodWall

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

def test_elevate_aggr_area():
    from flood_adapt.object_model.direct_impact.measure.elevate import Elevate

    test_toml = test_database / "charleston" / "input" / "measures" / "raise_property_aggregation_area" / "raise_property_aggregation_area.toml"
    assert test_toml.is_file()
    measure = Elevate().load(test_toml)

    assert measure.name == "raise_property_aggregation_area"
    assert measure.long_name == "raise_property_aggregation_area"
    assert measure.type == "elevate_properties"
    assert measure.elevation["value"] == 1
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.selection_type == "aggregation_area"
    assert measure.aggregation_area == "test_area_1"

def test_elevate_polygon():
    from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
    import geopandas as gpd
    
    test_toml = test_database / "charleston" / "input" / "measures" / "raise_property_polygon" / "raise_property_polygon.toml"
    assert test_toml.is_file()
    measure = Elevate().load(test_toml)

    assert measure.name == "raise_property_polygon"
    assert measure.long_name == "raise_property_polygon"
    assert measure.type == "elevate_properties"
    assert measure.elevation["value"] == 1
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.selection_type == "polygon"
    assert measure.polygon_file == "raise_property_polygon.geojson"

    polygon = gpd.read_file(Path(measure.config_file).parent / measure.polygon_file)
    assert isinstance(polygon, gpd.GeoDataFrame)