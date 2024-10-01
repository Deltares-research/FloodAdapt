import numpy as np
import pandas as pd
import pytest

from flood_adapt.object_model.hazard.interface.models import DEFAULT_TIMESTEP

__all__ = [
    "dummy_1d_timeseries_df",
    "dummy_2d_timeseries_df",
    "START_TIME",
    "END_TIME",
    "DEFAULT_TIMESTEP",
]


START_TIME = "2021-01-01 00:00:00"
END_TIME = "2021-01-01 01:00:00"


@pytest.fixture(scope="function")
def dummy_1d_timeseries_df() -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(1)


@pytest.fixture(scope="function")
def dummy_2d_timeseries_df() -> pd.DataFrame:
    return _n_dim_dummy_timeseries_df(2)


@pytest.fixture(scope="session")
def mock_download_meteo():
    return None  # TODO implement


def _n_dim_dummy_timeseries_df(n_dims: int) -> pd.DataFrame:
    time = pd.date_range(
        start=START_TIME, end=END_TIME, freq=DEFAULT_TIMESTEP.to_timedelta()
    )
    gen = np.random.default_rng()
    data = {f"data_{i}": gen.random(len(time)) for i in range(n_dims)}
    df = pd.DataFrame(index=time, data=data, dtype=float)
    df.index.name = "time"
    return df
