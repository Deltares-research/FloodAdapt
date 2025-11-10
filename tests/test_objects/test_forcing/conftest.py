import pytest

from flood_adapt.config.hazard import DataFrameContainer


@pytest.fixture
def scs_curves(test_data_dir) -> DataFrameContainer:
    return DataFrameContainer(path=test_data_dir / "scs_rainfall.csv")
