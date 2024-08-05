from pathlib import Path

import pytest

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.strategy import Strategy

test_database = Path().absolute() / "tests" / "test_database"


@pytest.fixture()
def test_attrs():
    strat_attrs = {
        "name": "new_strategy",
        "description": "new_unsaved_strategy",
        "measures": [
            "seawall",
            "raise_property_aggregation_area",
            "buyout",
            "floodproof",
        ],
    }
    yield strat_attrs


@pytest.fixture()
def test_seawall():
    attrs = {
        "name": "seawall",
        "description": "seawall",
        "type": "floodwall",
        "selection_type": "polygon",
        "polygon_file": "seawall.geojson",
        "elevation": {
            "value": 12,
            "units": "feet",
        },
    }
    return attrs


@pytest.fixture()
def test_raise_property_aggregation_area():
    attrs = {
        "name": "raise_property_aggregation_area",
        "description": "raise_property_aggregation_area",
        "type": "elevate_properties",
        "elevation": {
            "value": 1,
            "units": "feet",
            "type": "floodmap",
        },
        "selection_type": "aggregation_area",
        "aggregation_area_type": "aggr_lvl_2",
        "aggregation_area_name": "name5",
        "property_type": "RES",
    }
    return attrs


@pytest.fixture()
def test_buyout():
    attrs = {
        "name": "buyout",
        "description": "buyout",
        "type": "buyout_properties",
        "selection_type": "aggregation_area",
        "aggregation_area_type": "aggr_lvl_2",
        "aggregation_area_name": "name1",
        "property_type": "RES",
    }
    return attrs


@pytest.fixture()
def test_floodproof():
    attrs = {
        "name": "floodproof",
        "description": "floodproof",
        "type": "floodproof_properties",
        "selection_type": "aggregation_area",
        "aggregation_area_type": "aggr_lvl_2",
        "aggregation_area_name": "name3",
        "elevation": {
            "value": 3,
            "units": "feet",
        },
        "property_type": "RES",
    }
    return attrs


def test_strategy_comb_read(test_db):
    test_toml = (
        test_db.input_path / "strategies" / "strategy_comb" / "strategy_comb.toml"
    )
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)

    assert strategy.attrs.name == "strategy_comb"
    assert strategy.attrs.description == "strategy_comb"
    assert len(strategy.attrs.measures) == 4
    assert isinstance(strategy.get_hazard_strategy(), HazardStrategy)
    assert isinstance(strategy.get_impact_strategy(), ImpactStrategy)
    assert all(
        isinstance(measure, ImpactMeasure)
        for measure in strategy.get_impact_strategy().measures
    )
    assert all(
        isinstance(measure, HazardMeasure)
        for measure in strategy.get_hazard_strategy().measures
    )
    assert isinstance(strategy.get_impact_strategy().measures[0], Elevate)
    assert isinstance(strategy.get_impact_strategy().measures[1], Buyout)
    assert isinstance(strategy.get_impact_strategy().measures[2], FloodProof)
    assert isinstance(strategy.get_hazard_strategy().measures[0], FloodWall)


def test_strategy_no_measures(test_db):
    test_toml = test_db.input_path / "strategies" / "no_measures" / "no_measures.toml"
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)
    assert len(strategy.attrs.measures) == 0
    assert isinstance(strategy.get_hazard_strategy(), HazardStrategy)
    assert isinstance(strategy.get_impact_strategy(), ImpactStrategy)
    assert len(strategy.get_hazard_strategy().measures) == 0
    assert len(strategy.get_impact_strategy().measures) == 0


def test_elevate_comb_correct(test_db):
    test_toml = (
        test_db.input_path
        / "strategies"
        / "elevate_comb_correct"
        / "elevate_comb_correct.toml"
    )
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)

    assert strategy.attrs.name == "elevate_comb_correct"
    assert strategy.attrs.description == "elevate_comb_correct"
    assert isinstance(strategy.attrs.measures, list)
    assert isinstance(strategy.get_impact_strategy().measures[0], Elevate)
    assert isinstance(strategy.get_impact_strategy().measures[1], Elevate)


def test_green_infra(test_db):
    test_toml = test_db.input_path / "strategies" / "greeninfra" / "greeninfra.toml"
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)

    assert strategy.attrs.name == "greeninfra"
    assert isinstance(strategy.attrs.measures, list)
    assert isinstance(strategy.get_hazard_strategy().measures[0], GreenInfrastructure)
    assert isinstance(strategy.get_hazard_strategy().measures[1], GreenInfrastructure)
    assert isinstance(strategy.get_hazard_strategy().measures[2], GreenInfrastructure)
