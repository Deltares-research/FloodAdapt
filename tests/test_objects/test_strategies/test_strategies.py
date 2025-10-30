from unittest.mock import patch

import pytest

from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.objects import Strategy
from flood_adapt.objects.measures.measures import (
    HazardMeasure,
    ImpactMeasure,
    MeasureType,
)


def test_strategy_no_measures(strategy_no_measures: Strategy):
    strategy = strategy_no_measures

    assert len(strategy.measures) == 0
    assert isinstance(strategy.get_hazard_strategy(), Strategy)
    assert isinstance(strategy.get_impact_strategy(), Strategy)
    assert len(strategy.get_hazard_strategy().measures) == 0
    assert len(strategy.get_impact_strategy().measures) == 0


def test_get_impact_strategy(strategy_all_measures: Strategy):
    strategy = strategy_all_measures
    impact_strategy = strategy.get_impact_strategy()

    assert isinstance(impact_strategy, Strategy)
    assert 0 < len(impact_strategy.measures) <= len(strategy.measures)
    assert impact_strategy._measure_objects is not None
    for measure in impact_strategy._measure_objects:
        assert MeasureType.is_impact(measure.type)
        assert isinstance(measure, ImpactMeasure)


def test_get_hazard_strategy(strategy_all_measures: Strategy):
    strategy = strategy_all_measures
    hazard_strategy = strategy.get_hazard_strategy()

    assert isinstance(hazard_strategy, Strategy)
    assert 0 < len(hazard_strategy.measures) <= len(strategy.measures)
    assert hazard_strategy._measure_objects is not None
    for measure in hazard_strategy._measure_objects:
        assert MeasureType.is_hazard(measure.type)
        assert isinstance(measure, HazardMeasure)


def test_get_impact_measures(strategy_all_measures: Strategy):
    strategy = strategy_all_measures
    impact_measures = strategy.get_impact_measures()

    assert isinstance(impact_measures, list)
    assert len(impact_measures) > 0
    for measure in impact_measures:
        assert MeasureType.is_impact(measure.type)
        assert isinstance(measure, ImpactMeasure)


def test_get_hazard_measures(strategy_all_measures: Strategy):
    strategy = strategy_all_measures
    hazard_measures = strategy.get_hazard_measures()

    assert isinstance(hazard_measures, list)
    assert len(hazard_measures) > 0
    for measure in hazard_measures:
        assert MeasureType.is_hazard(measure.type)
        assert isinstance(measure, HazardMeasure)


@patch("flood_adapt.adapter.fiat_adapter.FiatAdapter.get_object_ids")
def test_check_overlapping_measures(
    mock_get_object_ids, strategy_with_overlapping_measures: Strategy, test_db
):
    strategy = strategy_with_overlapping_measures
    mock_get_object_ids.return_value = [1, 2, 3]

    for measure in strategy.get_measures():
        test_db.measures.save(measure)
    with pytest.raises(DatabaseError) as excinfo:
        test_db.strategies._check_overlapping_measures(strategy.measures)

    assert (
        "Cannot create strategy! There are overlapping buildings for which measures are proposed"
        in str(excinfo.value)
    )
