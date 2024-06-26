from pathlib import Path

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
