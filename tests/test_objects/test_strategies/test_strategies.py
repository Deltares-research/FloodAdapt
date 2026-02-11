from unittest.mock import patch

import pytest

from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.objects import Strategy
from flood_adapt.objects.measures.measures import (
    HazardMeasure,
    ImpactMeasure,
    MeasureType,
)
from tests.test_objects.test_measures.test_measures import (
    test_buyout,
    test_elevate,
    test_floodproof,
    test_floodwall,
    test_green_infra,
    test_pump,
)

__all__ = [
    "test_buyout",
    "test_elevate",
    "test_floodproof",
    "test_floodwall",
    "test_green_infra",
    "test_pump",
]


@pytest.fixture()
def strategy_no_measures() -> Strategy:
    s = Strategy(
        name="no_measures",
        description="test strategy with no measures",
        measures=[],
    )
    s.initialize_measure_objects(measures=[])
    return s


@pytest.fixture()
def test_strategy(
    test_elevate,
    test_buyout,
    test_floodproof,
    test_floodwall,
    test_green_infra,
    test_pump,
) -> Strategy:
    measure_objs = [
        test_elevate,
        test_buyout,
        test_floodproof,
        test_floodwall,
        test_green_infra,
        test_pump,
    ]
    s = Strategy(
        name="strategy_comb",
        description="test strategy with both hazard and impact measures",
        measures=[measure.name for measure in measure_objs],
    )
    s.initialize_measure_objects(measures=measure_objs)
    return s


def test_strategy_save_load_eq(tmp_path, test_strategy: Strategy):
    strategy = test_strategy
    assert strategy.name == "strategy_comb"
    assert len(strategy.measures) == 6

    impact_strategy = strategy.get_impact_strategy()
    impact_measures = strategy.get_impact_measures()
    assert isinstance(impact_strategy, Strategy)
    assert isinstance(impact_measures, list)
    for measure in impact_measures:
        assert MeasureType.is_impact(measure.type)
        assert isinstance(measure, ImpactMeasure)

    hazard_strategy = strategy.get_hazard_strategy()
    hazard_measures = strategy.get_hazard_measures()
    assert isinstance(hazard_strategy, Strategy)
    assert isinstance(hazard_measures, list)
    for measure in strategy.get_hazard_measures():
        assert MeasureType.is_hazard(measure.type)
        assert isinstance(measure, HazardMeasure)

    path = tmp_path / (test_strategy.name + ".toml")
    strategy.save(path)
    loaded = Strategy.load_file(path)
    assert loaded == strategy


def test_strategy_no_measures(strategy_no_measures: Strategy):
    strategy = strategy_no_measures
    assert len(strategy.measures) == 0
    assert isinstance(strategy.get_hazard_strategy(), Strategy)
    assert isinstance(strategy.get_impact_strategy(), Strategy)
    assert len(strategy.get_hazard_strategy().measures) == 0
    assert len(strategy.get_impact_strategy().measures) == 0


@pytest.fixture()
def setup_strategy_with_overlapping_measures(test_db, test_buyout):
    measures = []
    for i in range(1, 4):
        measure = test_buyout.model_copy(deep=True)
        measure.name = f"test_buyout_{i}"
        measures.append(measure)
        test_db.measures.add(measure)

    strategy = Strategy(
        name="test_strategy",
        description="test_strategy",
        measures=[measure.name for measure in measures],
    )
    strategy.initialize_measure_objects(measures=measures)
    return test_db, strategy


@patch("flood_adapt.adapter.fiat_adapter.FiatAdapter.get_object_ids")
def test_check_overlapping_measures(
    mock_get_object_ids, setup_strategy_with_overlapping_measures
):
    test_db, strategy = setup_strategy_with_overlapping_measures
    mock_get_object_ids.return_value = [1, 2, 3]

    with pytest.raises(DatabaseError) as excinfo:
        test_db.strategies._assert_no_overlapping_measures(strategy.measures)

    assert (
        "Cannot create strategy! There are overlapping buildings for which measures are proposed"
        in str(excinfo.value)
    )
