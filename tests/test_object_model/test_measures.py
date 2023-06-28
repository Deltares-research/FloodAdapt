from pathlib import Path

import geopandas as gpd
import tomli

from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.pump import Pump
from flood_adapt.object_model.interface.measures import (
    HazardType,
    ImpactType,
    SelectionType,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulLength,
    UnitfulLengthRefValue,
)

test_database = Path().absolute() / "tests" / "test_database"


def test_floodwall_read():
    test_toml = (
        test_database / "charleston" / "input" / "measures" / "seawall" / "seawall.toml"
    )
    assert test_toml.is_file()

    floodwall = FloodWall.load_file(test_toml)

    assert isinstance(floodwall.attrs.name, str)
    assert isinstance(floodwall.attrs.long_name, str)
    assert isinstance(floodwall.attrs.type, HazardType)
    assert isinstance(floodwall.attrs.elevation, UnitfulLength)

    assert floodwall.attrs.name == "seawall"
    assert floodwall.attrs.long_name == "seawall"
    assert floodwall.attrs.type == "floodwall"
    assert floodwall.attrs.elevation.value == 12
    assert floodwall.attrs.elevation.units == "feet"


def test_elevate_aggr_area_read():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.attrs.name, str)
    assert isinstance(elevate.attrs.long_name, str)
    assert isinstance(elevate.attrs.type, ImpactType)
    assert isinstance(elevate.attrs.elevation, UnitfulLengthRefValue)
    assert isinstance(elevate.attrs.selection_type, SelectionType)
    assert isinstance(elevate.attrs.aggregation_area_name, str)

    assert elevate.attrs.name == "raise_property_aggregation_area"
    assert elevate.attrs.long_name == "raise_property_aggregation_area"
    assert elevate.attrs.type == "elevate_properties"
    assert elevate.attrs.elevation.value == 1
    assert elevate.attrs.elevation.units == "feet"
    assert elevate.attrs.elevation.type == "floodmap"
    assert elevate.attrs.selection_type == "aggregation_area"
    assert elevate.attrs.aggregation_area_type == "aggr_lvl_2"
    assert elevate.attrs.aggregation_area_name == "name5"


def test_elevate_aggr_area_read_fail():
    # TODO validators do not work?
    test_dict = {
        "name": "test1",
        "long_name": "test1",
        "type": "elevate_properties",
        "elevation": {"value": 1, "units": "feet", "type": "floodmap"},
        "selection_type": "aggregation_area",
        # "aggregation_area_name": "test_area",
        "property_type": "RES",
    }

    Elevate.load_dict(test_dict, test_database / "charleston" / "input")


def test_elevate_aggr_area_save():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area.toml"
    )

    test_toml_new = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "raise_property_aggregation_area"
        / "raise_property_aggregation_area_new.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    elevate.save(test_toml_new)

    with open(test_toml, mode="rb") as fp:
        test_toml_dict = tomli.load(fp)
    with open(test_toml_new, mode="rb") as fp:
        test_toml_dict_new = tomli.load(fp)

    assert test_toml_dict == test_toml_dict_new


def test_elevate_polygon_read():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "raise_property_polygon"
        / "raise_property_polygon.toml"
    )
    assert test_toml.is_file()

    elevate = Elevate.load_file(test_toml)

    assert isinstance(elevate.attrs.name, str)
    assert isinstance(elevate.attrs.long_name, str)
    assert isinstance(elevate.attrs.type, ImpactType)
    assert isinstance(elevate.attrs.elevation, UnitfulLengthRefValue)
    assert isinstance(elevate.attrs.selection_type, SelectionType)
    assert isinstance(elevate.attrs.polygon_file, str)

    assert elevate.attrs.name == "raise_property_polygon"
    assert elevate.attrs.long_name == "raise_property_polygon"
    assert elevate.attrs.type == "elevate_properties"
    assert elevate.attrs.elevation.value == 1
    assert elevate.attrs.elevation.units == "feet"
    assert elevate.attrs.elevation.type == "floodmap"
    assert elevate.attrs.selection_type == "polygon"
    assert elevate.attrs.polygon_file == "raise_property_polygon.geojson"

    polygon = gpd.read_file(Path(test_toml).parent / elevate.attrs.polygon_file)
    assert isinstance(polygon, gpd.GeoDataFrame)


def test_buyout_read():
    test_toml = (
        test_database / "charleston" / "input" / "measures" / "buyout" / "buyout.toml"
    )
    assert test_toml.is_file()

    buyout = Buyout.load_file(test_toml)

    assert isinstance(buyout.attrs.name, str)
    assert isinstance(buyout.attrs.long_name, str)
    assert isinstance(buyout.attrs.type, ImpactType)
    assert isinstance(buyout.attrs.selection_type, SelectionType)
    assert isinstance(buyout.attrs.aggregation_area_name, str)


def test_floodproof_read():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "floodproof"
        / "floodproof.toml"
    )
    assert test_toml.is_file()

    floodproof = FloodProof.load_file(test_toml)

    assert isinstance(floodproof.attrs.name, str)
    assert isinstance(floodproof.attrs.long_name, str)
    assert isinstance(floodproof.attrs.type, ImpactType)
    assert isinstance(floodproof.attrs.selection_type, SelectionType)
    assert isinstance(floodproof.attrs.aggregation_area_name, str)


def test_pump_read():
    test_toml = (
        test_database / "charleston" / "input" / "measures" / "pump" / "pump.toml"
    )

    assert test_toml.is_file()

    pump = Pump.load_file(test_toml)

    assert isinstance(pump.attrs.name, str)
    assert isinstance(pump.attrs.long_name, str)
    assert isinstance(pump.attrs.type, HazardType)
    assert isinstance(pump.attrs.discharge, UnitfulDischarge)

    test_geojson = (
        test_database
        / "charleston"
        / "input"
        / "measures"
        / "pump"
        / pump.attrs.polygon_file
    )

    assert test_geojson.is_file()
