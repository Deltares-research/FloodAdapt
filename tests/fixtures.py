from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from object_model.direct_impact.measure.buyout import Buyout
from object_model.hazard.interface.models import DEFAULT_TIMESTEP, TimeModel
from object_model.hazard.measure.pump import Pump
from object_model.interface.measures import (
    BuyoutModel,
    HazardType,
    ImpactType,
    PumpModel,
    SelectionType,
)
from object_model.interface.projections import (
    PhysicalProjectionModel,
    ProjectionModel,
    SocioEconomicChangeModel,
)
from object_model.interface.strategies import StrategyModel
from object_model.io import unit_system as us
from object_model.projection import Projection
from object_model.strategy import Strategy

__all__ = [
    "dummy_time_model",
    "dummy_1d_timeseries_df",
    "dummy_2d_timeseries_df",
    "dummy_projection",
    "dummy_buyout_measure",
    "dummy_pump_measure",
    "dummy_strategy",
    "DEFAULT_TIMESTEP",
]

TEST_DATA_DIR = Path(__file__).parent / "data"


@pytest.fixture(scope="function")
def dummy_time_model() -> TimeModel:
    return TimeModel()


@pytest.fixture(scope="function")
def dummy_1d_timeseries_df(dummy_time_model) -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(1, dummy_time_model)


@pytest.fixture(scope="function")
def dummy_2d_timeseries_df(dummy_time_model) -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(2, dummy_time_model)


@pytest.fixture()
def dummy_projection():
    model = ProjectionModel(
        name="dummy_projection",
        physical_projection=PhysicalProjectionModel(),
        socio_economic_change=SocioEconomicChangeModel(),
    )
    return Projection.load_dict(model)


@pytest.fixture()
def dummy_buyout_measure():
    model = BuyoutModel(
        name="dummy_buyout_measure",
        type=ImpactType.buyout_properties,
        selection_type=SelectionType.aggregation_area,
        aggregation_area_type="aggr_lvl_2",
        aggregation_area_name="name1",
        property_type="residential",
    )
    return Buyout.load_dict(model)


@pytest.fixture()
def dummy_pump_measure():
    model = PumpModel(
        name="dummy_pump_measure",
        type=HazardType.pump,
        selection_type=SelectionType.polyline,
        polygon_file=str(TEST_DATA_DIR / "pump.geojson"),
        discharge=us.UnitfulDischarge(value=100, units=us.UnitTypesDischarge.cfs),
    )

    return Pump.load_dict(model)


@pytest.fixture()
def dummy_strategy(test_db, dummy_buyout_measure, dummy_pump_measure):
    pump = dummy_pump_measure
    buyout = dummy_buyout_measure
    model = StrategyModel(
        name="dummy_strategy",
        description="",
        measures=[buyout.attrs.name, pump.attrs.name],
    )

    for measure in [buyout, pump]:
        test_db.measures.save(measure)

    return Strategy.load_dict(model)


def _n_dim_dummy_timeseries_df(n_dims: int, time_model: TimeModel) -> pd.DataFrame:
    time = pd.date_range(
        start=time_model.start_time,
        end=time_model.end_time,
        freq=time_model.time_step,
        name="time",
    )
    gen = np.random.default_rng()
    data = {f"data_{i}": gen.random(len(time)) for i in range(n_dims)}
    df = pd.DataFrame(index=time, data=data, dtype=float)
    return df
