from unittest.mock import patch

import pytest

from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    HazardMeasure,
    ImpactMeasure,
    MeasureType,
    SelectionType,
)
from flood_adapt.objects.strategies.strategies import Strategy


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


@pytest.fixture()
def test_strategy(test_db) -> Strategy:
    return test_db.strategies.get("strategy_comb")


def test_strategy_comb_read(test_db, test_strategy: Strategy):
    strategy = test_strategy
    assert strategy.name == "strategy_comb"
    assert len(strategy.measures) == 4

    impact_strategy = strategy.get_impact_strategy()
    impact_measures = strategy.get_impact_measures()
    assert isinstance(impact_strategy, Strategy)
    assert isinstance(impact_measures, list)
    for measure in impact_measures:
        assert MeasureType.is_impact(measure.type)
        assert isinstance(measure, ImpactMeasure)
    assert isinstance(impact_measures[0], Elevate)
    assert isinstance(impact_measures[1], Buyout)
    assert isinstance(impact_measures[2], FloodProof)

    hazard_strategy = strategy.get_hazard_strategy()
    hazard_measures = strategy.get_hazard_measures()
    assert isinstance(hazard_strategy, Strategy)
    assert isinstance(hazard_measures, list)
    for measure in strategy.get_hazard_measures():
        assert MeasureType.is_hazard(measure.type)
        assert isinstance(measure, HazardMeasure)
    assert isinstance(hazard_measures[0], FloodWall)


def test_strategy_no_measures(test_db):
    strategy: Strategy = test_db.strategies.get("no_measures")
    assert len(strategy.measures) == 0
    assert isinstance(strategy.get_hazard_strategy(), Strategy)
    assert isinstance(strategy.get_impact_strategy(), Strategy)
    assert len(strategy.get_hazard_strategy().measures) == 0
    assert len(strategy.get_impact_strategy().measures) == 0


def test_elevate_comb_correct(test_db):
    strategy: Strategy = test_db.strategies.get("elevate_comb_correct")
    impact_measures = strategy.get_impact_measures()

    assert strategy.name == "elevate_comb_correct"
    assert isinstance(impact_measures, list)
    assert isinstance(strategy.measures, list)
    assert isinstance(impact_measures[0], Elevate)
    assert isinstance(impact_measures[1], Elevate)


def test_green_infra(test_db):
    strategy: Strategy = test_db.strategies.get("greeninfra")

    assert strategy.name == "greeninfra"
    assert isinstance(strategy.measures, list)

    hazard_measures = strategy.get_hazard_measures()
    assert isinstance(hazard_measures, list)

    assert isinstance(hazard_measures[0], GreenInfrastructure)
    assert isinstance(hazard_measures[1], GreenInfrastructure)
    assert isinstance(hazard_measures[2], GreenInfrastructure)


@pytest.fixture()
def setup_strategy_with_overlapping_measures(test_db, test_data_dir):
    measures = []
    for i in range(1, 4):
        attrs = {
            "name": f"test_buyout{i}",
            "description": "test_buyout",
            "type": MeasureType.buyout_properties,
            "selection_type": SelectionType.polygon,
            "property_type": "RES",
            "polygon_file": str(test_data_dir / "polygon.geojson"),
        }
        test_buyout = Buyout(**attrs)

        measures.append(test_buyout.name)
        test_db.measures.save(test_buyout)

    strategy_model = {
        "name": "test_strategy",
        "description": "test_strategy",
        "measures": measures,
    }
    return test_db, Strategy(**strategy_model)


@patch("flood_adapt.adapter.fiat_adapter.FiatAdapter.get_object_ids")
def test_check_overlapping_measures(
    mock_get_object_ids, setup_strategy_with_overlapping_measures
):
    test_db, strategy = setup_strategy_with_overlapping_measures
    mock_get_object_ids.return_value = [1, 2, 3]

    with pytest.raises(DatabaseError) as excinfo:
        test_db.strategies._check_overlapping_measures(strategy.measures)

    assert (
        "Cannot create strategy! There are overlapping buildings for which measures are proposed"
        in str(excinfo.value)
    )
