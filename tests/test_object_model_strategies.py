from pathlib import Path
import pytest
import geopandas as gpd

test_database = Path().absolute() / 'tests' / 'test_database'


def test_elevate_comb_correct():
    from flood_adapt.object_model.strategy import Strategy

    test_toml = test_database / "charleston" / "input" / "strategies" / "elevate_comb_correct" / "elevate_comb_correct.toml"
    assert test_toml.is_file()

    test_strategies = Strategy(test_toml)
    test_strategies.load()
    

def test_elevate_comb_fail_1():
    from flood_adapt.object_model.strategy import Strategy

    test_toml = test_database / "charleston" / "input" / "strategies" / "elevate_comb_fail_1" / "elevate_comb_fail_1.toml"
    assert test_toml.is_file()

    test_strategies = Strategy(test_toml)
    with pytest.raises(ValueError):
        test_strategies.load()
    
def test_elevate_comb_fail_2():
    from flood_adapt.object_model.strategy import Strategy

    test_toml = test_database / "charleston" / "input" / "strategies" / "elevate_comb_fail_2" / "elevate_comb_fail_2.toml"
    assert test_toml.is_file()

    test_strategies = Strategy(test_toml)
    with pytest.raises(ValueError):
        test_strategies.load()

def test_elevate_aggr_area():
    from flood_adapt.object_model.measures.elevate import Elevate

    test_toml = test_database / "charleston" / "input" / "measures" / "raise_property_aggregation_area" / "raise_property_aggregation_area.toml"
    assert test_toml.is_file()
    measure = Elevate(test_toml).load()

    assert measure.name == "raise_property_aggregation_area"
    assert measure.long_name == "raise_property_aggregation_area"
    assert measure.type == "elevate_properties"
    assert measure.datum == 'NAVD 88'
    assert measure.elevation["value"] == 1
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.selection_type == "aggregation_area"
    assert measure.aggregation_area == "Rosemont"

def test_elevate_polygon():
    from flood_adapt.object_model.measures.elevate import Elevate

    test_toml = test_database / "charleston" / "input" / "measures" / "raise_property_import_polygon" / "raise_property_import_polygon.toml"
    assert test_toml.is_file()
    measure = Elevate(test_toml).load()

    assert measure.name == "raise_property_import_polygon"
    assert measure.long_name == "raise_property_import_polygon"
    assert measure.type == "elevate_properties"
    assert measure.datum == 'NAVD 88'
    assert measure.elevation["value"] == 1
    assert measure.elevation["units"] == "feet"
    assert measure.elevation["type"] == "floodmap"
    assert measure.selection_type == "polygon"
    assert measure.polygon_file == "raise_property_import_polygon.geojson"

    polygon = gpd.read_file(Path(measure.config_file).parent / measure.polygon_file)
    assert isinstance(polygon, gpd.GeoDataFrame)