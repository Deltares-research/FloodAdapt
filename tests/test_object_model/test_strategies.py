from pathlib import Path

import pytest

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.strategy import Strategy

test_database = Path().absolute() / "tests" / "test_database"


def test_strategy_comb_read():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "strategy_comb"
        / "strategy_comb.toml"
    )
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)

    assert strategy.attrs.name == "strategy_comb"
    assert strategy.attrs.long_name == "strategy_comb"
    assert len(strategy.attrs.measures) == 3
    assert isinstance(strategy.get_hazard_strategy(), HazardStrategy)
    assert isinstance(strategy.get_impact_strategy(), ImpactStrategy)
    assert all(
        [
            isinstance(measure, ImpactMeasure)
            for measure in strategy.get_impact_strategy().measures
        ]
    )
    assert all(
        [
            isinstance(measure, HazardMeasure)
            for measure in strategy.get_hazard_strategy().measures
        ]
    )
    assert isinstance(strategy.get_impact_strategy().measures[0], Elevate)
    assert isinstance(strategy.get_impact_strategy().measures[1], Elevate)
    assert isinstance(strategy.get_hazard_strategy().measures[0], FloodWall)


def test_strategy_no_measures():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "no_measures"
        / "no_measures.toml"
    )
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)
    assert len(strategy.attrs.measures) == 0
    assert isinstance(strategy.get_hazard_strategy(), HazardStrategy)
    assert isinstance(strategy.get_impact_strategy(), ImpactStrategy)
    assert len(strategy.get_hazard_strategy().measures) == 0
    assert len(strategy.get_impact_strategy().measures) == 0


def test_elevate_comb_correct():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_correct"
        / "elevate_comb_correct.toml"
    )
    assert test_toml.is_file()

    strategy = Strategy.load_file(test_toml)

    assert strategy.attrs.name == "elevate_comb_correct"
    assert strategy.attrs.long_name == "elevate_comb_correct"
    assert isinstance(strategy.attrs.measures, list)
    assert isinstance(strategy.get_impact_strategy().measures[0], Elevate)
    assert isinstance(strategy.get_impact_strategy().measures[1], Elevate)


def test_elevate_comb_fail_1():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_fail_1"
        / "elevate_comb_fail_1.toml"
    )
    assert test_toml.is_file()

    with pytest.raises(ValueError):
        Strategy.load_file(test_toml)


def test_elevate_comb_fail_2():
    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_fail_2"
        / "elevate_comb_fail_2.toml"
    )
    assert test_toml.is_file()

    with pytest.raises(ValueError):
        Strategy.load_file(test_toml)
