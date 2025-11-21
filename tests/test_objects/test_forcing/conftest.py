import pandas as pd
import pytest

from flood_adapt.config.hazard import DataFrameContainer


@pytest.fixture
def rainfall_scs_curves(test_data_dir) -> pd.DataFrame:
    return pd.read_csv(test_data_dir / "rainfall_scs_curves.csv")


@pytest.fixture
def scs_curves(rainfall_scs_curves: pd.DataFrame) -> DataFrameContainer:
    container = DataFrameContainer(name="scs")
    container.set_data(rainfall_scs_curves)
    return container
