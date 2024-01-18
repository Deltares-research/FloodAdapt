from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from flood_adapt.dbs_classes.dbs_measure import DbsMeasure


class DummyMeasure:
    def __init__(self):
        self.attrs = {}
        self.attrs["name"] = "some_measure_name"

        self.database_input_path = Path("some_fake_path")


class TestDbsMeasure:
    @pytest.fixture(autouse=True)
    def setup(self):
        mock_database_object = Mock()
        mock_database_object.input_path = Path("some_fake_path")

        self.dbs_measure = DbsMeasure(mock_database_object)

        dummy_measure = DummyMeasure()

        with patch(
            "flood_adapt.dbs_classes.dbs_measure.MeasureFactory.get_measure_object",
            return_value=dummy_measure,
        ) as mock_factory:
            yield mock_factory

    def test_get(self, setup):
        # Arrange
        mock_measure_factory = setup

        # Act
        measure = self.dbs_measure.get("some_measure_name")

        # Assert
        assert measure.attrs["name"] == "some_measure_name"
        mock_measure_factory.assert_called_once_with(
            Path("some_fake_path/measures/some_measure_name/some_measure_name.toml")
        )
