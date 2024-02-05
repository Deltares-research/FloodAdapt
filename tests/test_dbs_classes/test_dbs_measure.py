from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from flood_adapt.dbs_classes.dbs_measure import DbsMeasure


class SomeDummyMeasure:
    def __init__(self):
        self.attrs = {}
        self.attrs["name"] = "some_measure_name"
        self.attrs["description"] = "some_description"
        self.attrs["type"] = "some_type"
        self.attrs["lock_count"] = 0

        self.database_input_path = Path("some_fake_path")

class AnotherDummyMeasure:
    def __init__(self):
        self.attrs = {}
        self.attrs["name"] = "another_measure_name"
        self.attrs["description"] = "another_description"
        self.attrs["type"] = "another_type"
        self.attrs["lock_count"] = 0

        self.database_input_path = Path("another_fake_path")

class TestDbsMeasure:
    @pytest.fixture(autouse=True)
    def setup(self):
        mock_database_object = Mock()
        mock_database_object.input_path = Path("some_fake_path")

        self.dbs_measure = DbsMeasure(mock_database_object)

        # Mock the MeasureFactory.get_measure_object method
        dummy_measure = SomeDummyMeasure()
        another_dummy_measure = AnotherDummyMeasure()

        def side_effect(arg):
            # Input for the side_effect is the measure name
            if str(arg) == 'some_fake_path\\measures\\some_measure_name\\some_measure_name.toml':
                return dummy_measure
            elif str(arg) == 'some_fake_path\\measures\\some_measure_name\\another_measure_name.toml':
                return another_dummy_measure
            else:
                raise FileNotFoundError("File not found")

        # Set up the mock iterdir function
        mock_path1 = MagicMock(spec=Path)
        mock_path2 = MagicMock(spec=Path)

        # Set the st_mtime attribute and other necessary attributes
        mock_path1.st_mtime = 1234567890
        mock_path1.name = 'some_measure_name'
        mock_path2.st_mtime = 1234567891
        mock_path2.name = 'another_measure_name'

        # Set up the mock iterdir function
        mock_iterdir_return_value = [mock_path1, mock_path2]

        # Patch the iterdir method on the input_path object and the get_measure_object function
        with patch.object(Path, 'iterdir', return_value=mock_iterdir_return_value), \
            patch("flood_adapt.dbs_classes.dbs_measure.MeasureFactory.get_measure_object", side_effect=side_effect) as mock_factory:
            # Now when you call Path in the module, it will return the mock Path object
            # And when you call iterdir on the mock Path object, it will return the list of paths
            # Also, when you call get_measure_object, it will call side_effect with its arguments and return its result
            yield mock_factory

    def test_get_object_file_found(self, setup):
        # Arrange
        mock_measure_factory = setup

        # Act
        measure = self.dbs_measure.get("some_measure_name")

        # Assert
        assert measure.attrs["name"] == "some_measure_name"
        mock_measure_factory.assert_called_once_with(
            Path("some_fake_path/measures/some_measure_name/some_measure_name.toml")
        )

    def test_list_objects(self, setup):
        # Act
        objects = self.dbs_measure.list_objects()

        # Assert
        assert objects["name"] == ["some_measure_name", "another_measure_name"]
        assert objects["description"] == ["some_description", "another_description"]
        assert objects["objects"][0].attrs["name"] == "some_measure_name"
        assert objects["objects"][1].attrs["name"] == "another_measure_name"
        setup.assert_called_once()
