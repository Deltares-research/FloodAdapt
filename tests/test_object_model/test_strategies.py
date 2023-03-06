from pathlib import Path
import pytest

test_database = Path().absolute() / "tests" / "test_database"


def test_strategy_comb():
    from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
    from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
    from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
    from flood_adapt.object_model.hazard.measure.floodwall import FloodWall

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "strategy_comb"
        / "strategy_comb.toml"
    )
    assert test_toml.is_file()

    test_strategies_impact = ImpactStrategy().load(test_toml)
    test_strategies_hazard = HazardStrategy().load(test_toml)
    assert len(test_strategies_impact.measures) == 2
    assert len(test_strategies_hazard.measures) == 1
    assert isinstance(test_strategies_impact.measures[0], Elevate)
    assert isinstance(test_strategies_impact.measures[1], Elevate)
    assert isinstance(test_strategies_hazard.measures[0], FloodWall)


def test_strategy_no_measures():
    from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
    from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "no_measures"
        / "no_measures.toml"
    )
    assert test_toml.is_file()

    test_strategies_impact = ImpactStrategy().load(test_toml)
    test_strategies_hazard = HazardStrategy().load(test_toml)
    assert len(test_strategies_impact.measures) == 0
    assert len(test_strategies_hazard.measures) == 0


def test_elevate_comb_correct():
    from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
    from flood_adapt.object_model.direct_impact.measure.elevate import Elevate

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_correct"
        / "elevate_comb_correct.toml"
    )
    assert test_toml.is_file()

    test_strategies = ImpactStrategy().load(test_toml)

    assert test_strategies.name == "elevate_comb_correct"
    assert test_strategies.long_name == "elevate_comb_correct"
    assert isinstance(test_strategies.measures, list)
    assert isinstance(test_strategies.measures[0], Elevate)
    assert isinstance(test_strategies.measures[1], Elevate)


def test_elevate_comb_fail_1():
    from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_fail_1"
        / "elevate_comb_fail_1.toml"
    )
    assert test_toml.is_file()

    test_strategies = ImpactStrategy()
    with pytest.raises(ValueError):
        test_strategies.load(test_toml)


def test_elevate_comb_fail_2():
    from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy

    test_toml = (
        test_database
        / "charleston"
        / "input"
        / "strategies"
        / "elevate_comb_fail_2"
        / "elevate_comb_fail_2.toml"
    )
    assert test_toml.is_file()

    test_strategies = ImpactStrategy()
    with pytest.raises(ValueError):
        test_strategies.load(test_toml)
