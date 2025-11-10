import pytest

from flood_adapt.objects import (
    Buyout,
    MeasureType,
    SelectionType,
    Strategy,
)
from flood_adapt.objects.data_container import GeoDataFrameContainer
from tests.test_objects.test_measures.conftest import (
    test_buyout,
    test_elevate,
    test_floodproof,
    test_green_infra,
    test_pump,
)

__all__ = [
    "test_buyout",
    "test_elevate",
    "test_floodproof",
    "test_green_infra",
    "test_pump",
]


## Strategy Fixtures ##
@pytest.fixture()
def strategy_all_measures(
    test_elevate, test_pump, test_buyout, test_floodproof, test_green_infra
) -> Strategy:
    measures = [test_elevate, test_pump, test_buyout, test_floodproof, test_green_infra]
    strategy = Strategy(name="strategy_all_measures")
    strategy.set_measures(measures)
    return strategy


@pytest.fixture()
def strategy_no_measures() -> Strategy:
    strategy = Strategy(name="no_measures")
    strategy.set_measures([])
    return strategy


@pytest.fixture()
def strategy_with_overlapping_measures(gdf_container_polygon: GeoDataFrameContainer):
    measures = []
    for i in range(1, 4):
        test_buyout = Buyout(
            name=f"test_buyout{i}",
            description="test_buyout",
            type=MeasureType.buyout_properties,
            selection_type=SelectionType.polygon,
            property_type="RES",
            gdf=gdf_container_polygon,
        )

        measures.append(test_buyout)

    strategy = Strategy(name="test_strategy_overlap")
    strategy.set_measures(measures)

    return strategy
