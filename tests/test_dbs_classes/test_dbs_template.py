import os
import time
from pathlib import Path
from unittest.mock import Mock, patch
from typing import Any, Union
import datetime
import geopandas as gpd
import pytest
from shapely.geometry import LineString

from flood_adapt.dbs_classes.dbs_template import DbsTemplate


### Some dummy classes to be used in the tests

class DummyObjectModel:
    name: str = "dummy_name"
    description: str = "dummy_description"

class DummyObject:
    attrs: DummyObjectModel = DummyObjectModel()
    database_input_path = Path("some_fake_path")

    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        return DummyObject()

    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        return DummyObject()

    def save(self, filepath: Union[str, os.PathLike]):
        """save object attributes to a toml file"""
        pass


### End of dummy classes
        
### Fixtures
@pytest.fixture
def mock_database_object():
    mock_database_object = Mock()
    mock_database_object.input_path = Path("some_fake_path")
    mock_database_object.aggr_areas = {
        "some_aggregation_area_type": gpd.GeoDataFrame(
            data={"name": ["dummy_aggregation_area"]},
            geometry=[LineString([(0, 0), (1, 1)])],
        )
    }
    return mock_database_object


# @pytest.fixture
# def dbs_measure(mock_database_object):
#     return DbsMeasure(mock_database_object)


# @pytest.fixture(params=[["SomeDummyMeasure", "AnotherDummyMeasure", "DummyMeasureWithPolygon", "DummyMeasureWithAggregationArea"]])
# def dummy_measures(request):
#     return [MEASURES_DICT[name] for name in request.param]


# @pytest.fixture
# def mock_paths(dummy_measures):
#     mock_path = [MagicMock(spec=Path) for _ in dummy_measures]
#     for path, measure in zip(mock_path, dummy_measures):
#         path.name = measure.attrs.name
#         path.__truediv__.return_value = Path(measure._get_toml_path())
#     return mock_path


# @pytest.fixture
# def mock_path_stats():
#     return os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0))


@pytest.fixture
def patch_is_file():
    patcher = patch('os.path.isfile')
    mock_exists = patcher.start()
    mock_exists.return_value = True
    yield mock_exists
    patcher.stop()

@pytest.fixture
def patch_is_not_file():
    patcher = patch('os.path.isfile')
    mock_exists = patcher.start()
    mock_exists.return_value = False
    yield mock_exists
    patcher.stop()

# @pytest.fixture
# def patch_file_exists():
#     with patch.object(Path, "exists", return_value=True) as mock_exists:
#         yield mock_exists


# @pytest.fixture
# def patch_file_not_exists():
#     with patch.object(Path, "exists", return_value=False) as mock_exists:
#         yield mock_exists

@pytest.fixture
def patch_iterdir():
    mock_paths = [Path("some_fake_path/dummy_name") for _ in range(4)]
    with patch.object(Path, "iterdir", return_value=mock_paths) as mock_iterdir:
        yield mock_iterdir


@pytest.fixture
def patch_stat():
    mock_path_stats = os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0))
    with patch.object(Path, "stat", return_value=mock_path_stats) as mock_stat:
        yield mock_stat


# @pytest.fixture
# def patch_geopandas(dummy_measures):
#     def geopandas_side_effect(arg):
#         for measure in dummy_measures:
#             if measure.attrs.polygon_file is None:
#                 continue
#             if arg == (measure._get_database_path() / measure.attrs.polygon_file):
#                 return measure._get_geopandas_mocked_value()
#         else:
#             raise FileNotFoundError("File not found")

#     with patch(
#         "geopandas.read_file", side_effect=geopandas_side_effect
#     ) as mock_geopandas:
#         yield mock_geopandas


# @pytest.fixture
# def patch_measure_factory(dummy_measures):
#     def MeasureFactory_side_effect(arg):
#         for measure in dummy_measures:
#             if arg == measure._get_toml_path():
#                 return measure
#         else:
#             raise FileNotFoundError("File not found")

#     with patch(
#         "flood_adapt.dbs_classes.dbs_measure.MeasureFactory.get_measure_object",
#         side_effect=MeasureFactory_side_effect,
#     ) as mock_factory:
#         yield mock_factory

# ### End of fixtures
        
### Tests
class TestDbsMeasure:    
    def test_getObject_fileFound(self, mock_database_object, patch_is_file):
        """Test that the get_object method returns the correct measure object when the file is found.
        
        Patches:
        - Path.is_file: to return True
        """

        # Arrange
        database_template_class = DbsTemplate( mock_database_object )
        database_template_class._object_model_class = DummyObject()


        # Act
        with patch_is_file:
            measure = database_template_class.get("dummy_name")

        # Assert
        assert measure.attrs.name == "dummy_name"
        assert measure.attrs.description == "dummy_description"
        patch_is_file.assert_called_once_with(Path("some_fake_path/dummy_name/dummy_name.toml"))

    def test_getObject_fileNotFound(self, mock_database_object, patch_is_not_file):
        """Test that the get_object method raises a ValueError when the file is not found.
        
        Patches:
        - Path.is_file: to return False
        """

        # Arrange
        database_template_class = DbsTemplate( mock_database_object )
        database_template_class._object_model_class = DummyObject()

        # Act
        with patch_is_not_file:
            with pytest.raises(ValueError) as excinfo:
                database_template_class.get("dummy_name")
        assert " 'dummy_name' does not exist." in str(excinfo.value)
        patch_is_not_file.assert_called_once_with(Path("some_fake_path/dummy_name/dummy_name.toml"))

    def test_getObjectList_happyFlow(
        self,
        mock_database_object,
        patch_iterdir,
        patch_stat,
    ):
        """Test that the list_objects method returns a dictionary with the correct information.	

        Patches:
        - Path.iterdir: to return a mocked list of paths
        - Path.stat: to return the mock path stats
        """
        # Arrange
        database_template_class = DbsTemplate( mock_database_object )
        database_template_class._object_model_class = DummyObject()

        # Act
        objects = database_template_class._get_object_list()

        # Assert
        assert objects["path"] == [Path("some_fake_path/dummy_name/dummy_name.toml")] * 4
        assert objects["last_modification_date"][0] == [datetime.datetime(1970, 1, 1, 1, 0)]*4
        assert patch_iterdir.call_count == 1
        assert patch_stat.call_count == 4

    def test_getObjectList_noMeasures(self, mock_database_object, patch_iterdir):
        """Test that the list_objects method returns an empty dictionary if no measures are found in the database.
        
        Patches:
        - Path.iterdir: to return an empty list
        """
        # Arrange
        database_template_class = DbsTemplate( mock_database_object )
        database_template_class._object_model_class = DummyObject()

        patch_iterdir.return_value = []

        # Act
        objects = database_template_class._get_object_list()

        # Assert
        assert objects == {'path': [], 'last_modification_date': []}
        assert patch_iterdir.call_count == 1   

    def test_listObjects_happyFlow(self, mock_database_object,
        patch_iterdir,
        patch_stat,
        patch_is_file):
        """Test that the list_objects method returns a dictionary with the correct information.

        Patches:
        - Path.iterdir: to return a mocked list of paths
        - Path.stat: to return the mock path stats
        - Path.is_file: to return True
        """
        # Arrange
        database_template_class = DbsTemplate( mock_database_object )
        database_template_class._object_model_class = DummyObject()

        # Act
        # Using this patch globaly breaks checking the call count of the patch
        with patch_is_file:
            objects = database_template_class.list_objects()

        # Assert
        assert objects["path"] == [Path("some_fake_path/dummy_name/dummy_name.toml")] * 4
        assert objects["last_modification_date"] == [datetime.datetime(1970, 1, 1, 1, 0)]*4
        assert objects["name"] == ["dummy_name"] * 4
        assert objects["description"] == ["dummy_description"] * 4
        assert type(objects["objects"][0]) == DummyObject
        assert type(objects["objects"][0].attrs) == DummyObjectModel
        assert objects["objects"][0].attrs.name == "dummy_name"
        assert objects["objects"][0].attrs.description == "dummy_description"
        assert objects["objects"][0].database_input_path == Path("some_fake_path")
        assert patch_iterdir.call_count == 1
        assert patch_stat.call_count == 4
        assert patch_is_file.call_count == 4
        assert patch_is_file.call_args_list == [
            Path("some_fake_path/dummy_name/dummy_name.toml") 
            ] * 4