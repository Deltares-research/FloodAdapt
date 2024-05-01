import os
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.object_model.interface.measures import MeasureModel


### Some dummy classes to be used in the tests
class TemplateDummyMeasure:

    database_input_path = Path("some_fake_path")

    # Not a real measure implementation, just for setting up the mock
    def _get_database_path(self):
        return self.database_input_path / "measures" / self.attrs.name

    def _get_toml_path(self):
        return (
            self.database_input_path
            / "measures"
            / self.attrs.name
            / f"{self.attrs.name}.toml"
        )

    def _get_geopandas_mocked_value(self):
        raise FileNotFoundError("Geometry file not found")


class SomeDummyMeasure(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "some_measure_name",
            "description": "some_description",
            "type": "some_type",
            "polygon_file": None,
            "aggregation_area_name": None,
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)


class AnotherDummyMeasure(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "another_measure_name",
            "description": "another_description",
            "type": "another_type",
            "polygon_file": None,
            "aggregation_area_name": None,
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)


class DummyMeasureWithPolygon(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "dummy_measure_with_polygon",
            "description": "dummy_description",
            "type": "linestring_type",
            "polygon_file": "dummy_measure_with_polygon.geojson",
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)

    def _get_geopandas_mocked_value(self):
        return gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1)])])


class DummyMeasureWithAggregationArea(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "dummy_measure_with_aggregation_area",
            "description": "dummy_description",
            "type": "aggregate_type",
            "polygon_file": None,
            "aggregation_area_name": "dummy_aggregation_area",
            "aggregation_area_type": "some_aggregation_area_type",
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)

class DummyMeasureWithIncorrectPolygon(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "dummy_measure_with_incorrect_polygon",
            "description": "dummy_description",
            "type": "linestring_type",
            "polygon_file": "non_existent_polygon.geojson",
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)

    def _get_geopandas_mocked_value(self):
        return gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1)])])
    
class DummyMeasureWithIncorrectAggregationArea(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "dummy_measure_with_incorrect_aggregation_area",
            "description": "dummy_description",
            "type": "aggregate_type",
            "polygon_file": None,
            "aggregation_area_name": "non_existent_aggregation_area",
            "aggregation_area_type": "some_aggregation_area_type",
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)

    def _get_geopandas_mocked_value(self):
        return gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1)])])
    
class DummyMeasureWithIncorrectAggregationAreaType(TemplateDummyMeasure):
    def __init__(self):
        model_dict = {
            "name": "dummy_measure_with_incorrect_aggregation_area_type",
            "description": "dummy_description",
            "type": "aggregate_type",
            "polygon_file": None,
            "aggregation_area_name": "dummy_aggregation_area",
            "aggregation_area_type": "non_existent_aggregation_area_type",
        }
        self.attrs = MeasureModel.__new__(MeasureModel)
        self.attrs.__dict__.update(model_dict)

    def _get_geopandas_mocked_value(self):
        return gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1)])])

# Define the measures as module-level constants  
SOME_DUMMY_MEASURE = SomeDummyMeasure()
ANOTHER_DUMMY_MEASURE = AnotherDummyMeasure()
DUMMY_MEASURE_WITH_POLYGON = DummyMeasureWithPolygon()
DUMMY_MEASURE_WITH_AGGREGATION_AREA = DummyMeasureWithAggregationArea()
DUMMY_MEASURE_WITH_INCORRECT_POLYGON = DummyMeasureWithIncorrectPolygon()
DUMMY_MEASURE_WITH_INCORRECT_AGGREGATION_AREA = DummyMeasureWithIncorrectAggregationArea()
DUMMY_MEASURE_WITH_INCORRECT_AGGREGATION_AREA_TYPE = DummyMeasureWithIncorrectAggregationAreaType()

# Define a mapping from string names to the actual measure objects
MEASURES_DICT = {
    "SomeDummyMeasure": SOME_DUMMY_MEASURE,
    "AnotherDummyMeasure": ANOTHER_DUMMY_MEASURE,
    "DummyMeasureWithPolygon": DUMMY_MEASURE_WITH_POLYGON,
    "DummyMeasureWithAggregationArea": DUMMY_MEASURE_WITH_AGGREGATION_AREA,
    "DummyMeasureWithIncorrectPolygon": DUMMY_MEASURE_WITH_INCORRECT_POLYGON,
    "DummyMeasureWithIncorrectAggregationArea": DUMMY_MEASURE_WITH_INCORRECT_AGGREGATION_AREA,
    "DummyMeasureWithIncorrectAggregationAreaType": DUMMY_MEASURE_WITH_INCORRECT_AGGREGATION_AREA_TYPE
}

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


@pytest.fixture
def dbs_measure(mock_database_object):
    return DbsMeasure(mock_database_object)


@pytest.fixture(params=[["SomeDummyMeasure", "AnotherDummyMeasure", "DummyMeasureWithPolygon", "DummyMeasureWithAggregationArea"]])
def dummy_measures(request):
    return [MEASURES_DICT[name] for name in request.param]


@pytest.fixture
def mock_paths(dummy_measures):
    mock_path = [MagicMock(spec=Path) for _ in dummy_measures]
    for path, measure in zip(mock_path, dummy_measures):
        path.name = measure.attrs.name
        path.__truediv__.return_value = Path(measure._get_toml_path())
    return mock_path


@pytest.fixture
def mock_path_stats():
    return os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0))


@pytest.fixture
def patch_file_exists():
    with patch.object(Path, "exists", return_value=True) as mock_exists:
        yield mock_exists


@pytest.fixture
def patch_file_not_exists():
    with patch.object(Path, "exists", return_value=False) as mock_exists:
        yield mock_exists

@pytest.fixture
def patch_iterdir(mock_paths):
    with patch.object(Path, "iterdir", return_value=mock_paths) as mock_iterdir:
        yield mock_iterdir


@pytest.fixture
def patch_stat(mock_path_stats):
    with patch.object(Path, "stat", return_value=mock_path_stats) as mock_stat:
        yield mock_stat


@pytest.fixture
def patch_geopandas(dummy_measures):
    def geopandas_side_effect(arg):
        for measure in dummy_measures:
            if measure.attrs.polygon_file is None:
                continue
            if arg == (measure._get_database_path() / measure.attrs.polygon_file):
                return measure._get_geopandas_mocked_value()
        else:
            raise FileNotFoundError("File not found")

    with patch(
        "geopandas.read_file", side_effect=geopandas_side_effect
    ) as mock_geopandas:
        yield mock_geopandas


@pytest.fixture
def patch_measure_factory(dummy_measures):
    def MeasureFactory_side_effect(arg):
        for measure in dummy_measures:
            if arg == measure._get_toml_path():
                return measure
        else:
            raise FileNotFoundError("File not found")

    with patch(
        "flood_adapt.dbs_classes.dbs_measure.MeasureFactory.get_measure_object",
        side_effect=MeasureFactory_side_effect,
    ) as mock_factory:
        yield mock_factory

### End of fixtures
        
### Tests
class TestDbsMeasure:
    def test_getObject_fileFound(self, dbs_measure, patch_measure_factory):
        """Test that the get_object method returns the correct measure object when the file is found.
        
        Patches:
        - MeasureFactory.get_measure_object: to return the correct measure object
        """

        # Arrange
        mock_measure_factory = patch_measure_factory

        # Act
        measure = dbs_measure.get("some_measure_name")

        # Assert
        assert measure.attrs.name == "some_measure_name"
        mock_measure_factory.assert_called_once_with(
            Path("some_fake_path/measures/some_measure_name/some_measure_name.toml")
        )

    def test_listObjects_happyFlow(
        self,
        dbs_measure,
        patch_file_exists,
        patch_iterdir,
        patch_stat,
        patch_geopandas,
        patch_measure_factory,
    ):
        """Test that the list_objects method returns a dictionary with the correct information.	

        Patches:
        - Path.exists: to return True for the geojson file
        - Path.iterdir: to return the mock paths
        - Path.stat: to return the mock path stats
        - MeasureFactory.get_measure_object: to return the correct measure object
        - geopandas.read_file: to return the correct geometry
        """
        # Arrange
        mock_factory = patch_measure_factory
        expected_factory_calls = [
            call(
                Path("some_fake_path/measures/some_measure_name/some_measure_name.toml")
            ),
            call(
                Path(
                    "some_fake_path/measures/another_measure_name/another_measure_name.toml"
                )
            ),
            call(
                Path(
                    "some_fake_path/measures/dummy_measure_with_polygon/dummy_measure_with_polygon.toml"
                )
            ),
            call(
                Path(
                    "some_fake_path/measures/dummy_measure_with_aggregation_area/dummy_measure_with_aggregation_area.toml"
                )
            ),
        ]
        expected_geopandas_calls = [
            call(
                Path(
                    "some_fake_path/measures/dummy_measure_with_polygon/dummy_measure_with_polygon.geojson"
                )
            ),
        ]

        # Act
        objects = dbs_measure.list_objects()

        # Assert
        assert objects["name"] == [
            "some_measure_name",
            "another_measure_name",
            "dummy_measure_with_polygon",
            "dummy_measure_with_aggregation_area",
        ]
        assert objects["description"] == [
            "some_description",
            "another_description",
            "dummy_description",
            "dummy_description",
        ]
        assert objects["objects"][0].attrs.name == "some_measure_name"
        assert objects["objects"][1].attrs.name == "another_measure_name"
        assert objects["objects"][2].attrs.name == "dummy_measure_with_polygon"
        assert objects["objects"][3].attrs.name == "dummy_measure_with_aggregation_area"
        assert objects["geometry"][0] is None
        assert objects["geometry"][1] is None
        assert objects["geometry"][2].equals(
            gpd.GeoDataFrame(geometry=[LineString([(0, 0), (1, 1)])])
        )
        assert objects["geometry"][3].equals(
            gpd.GeoDataFrame(
                {
                    "name": "dummy_aggregation_area",
                    "geometry": [LineString([(0, 0), (1, 1)])],
                }
            )
        )
        mock_factory.assert_has_calls(expected_factory_calls)
        patch_geopandas.assert_has_calls(expected_geopandas_calls)

    def test_listObjects_noMeasures(self, dbs_measure, patch_iterdir):
        """Test that the list_objects method returns an empty dictionary if no measures are found in the database.
        
        Patches:
        - Path.iterdir: to return an empty list
        """
        # Arrange
        mock_iterdir = patch_iterdir
        mock_iterdir.return_value = []

        # Act
        objects = dbs_measure.list_objects()

        # Assert
        assert objects == {'path': [], 'last_modification_date': [], 'name': [], 'description': [], 'objects': [], 'geometry': []}
        mock_iterdir.assert_called_once_with()

    def test_listObjects_geojsonNotFound(
        self, dbs_measure, patch_file_not_exists, patch_iterdir, patch_stat, patch_measure_factory
    ):
        """Test that the list_objects method raises a FileNotFoundError if the geojson file does not exist.

        Patches:
        - Path.exists: to return False for the geojson file
        - Path.iterdir: to return the mock paths
        - Path.stat: to return the mock path stats
        - MeasureFactory.get_measure_object: to return the correct measure object
        """

        # Act
        with pytest.raises(FileNotFoundError) as excinfo:
            dbs_measure.list_objects()
        assert (
            "Polygon file dummy_measure_with_polygon.geojson for measure dummy_measure_with_polygon does not exist."
            in str(excinfo.value)
        )

    @pytest.mark.parametrize("dummy_measures", [["DummyMeasureWithIncorrectAggregationArea"]], indirect=True)
    def test_listObjects_aggregationAreaNotFound(
        self, dummy_measures, dbs_measure, patch_file_exists, patch_iterdir, patch_stat, patch_measure_factory
    ):
        """
        Test that the list_objects method raises a ValueError if the aggregation area does not exist.
        
        Patches: 
        - Path.exists: to return True for the geojson file
        - Path.iterdir: to return the mock paths
        - Path.stat: to return the mock path stats
        - MeasureFactory.get_measure_object: to return the correct measure object
        """

        # Act
        with pytest.raises(ValueError) as excinfo:
            dbs_measure.list_objects()
        assert (
            "Aggregation area name non_existent_aggregation_area for measure dummy_measure_with_incorrect_aggregation_area does not exist."
            in str(excinfo.value)
        )

    @pytest.mark.parametrize("dummy_measures", [["DummyMeasureWithIncorrectAggregationAreaType"]], indirect=True)
    def test_listObjects_aggregationAreaTypeNotFound(
        self, dummy_measures, dbs_measure, patch_file_exists, patch_iterdir, patch_stat, patch_measure_factory
    ):
        """
        Test that the list_objects method raises a ValueError if the aggregation area type does not exist.

        Patches:
        - Path.exists: to return True for the geojson file
        - Path.iterdir: to return the mock paths
        - Path.stat: to return the mock path stats
        - MeasureFactory.get_measure_object: to return the correct measure object
        """

        # Act
        with pytest.raises(ValueError) as excinfo:
            dbs_measure.list_objects()
        assert (
            "Aggregation area type non_existent_aggregation_area_type for measure dummy_measure_with_incorrect_aggregation_area_type does not exist."
            in str(excinfo.value)
        )

    def test_setLock_happyFlow(self, dbs_measure, patch_measure_factory):
        """Test that the set_lock method sets the lock_count attribute of the measure object to 1.
        
        Patches:
        - MeasureFactory.get_measure_object: to return the correct measure object
        """
        # Arrange
        mock_factory = patch_measure_factory

        # Act
        dbs_measure.set_lock(name = "some_measure_name")

        # Assert
        assert dbs_measure.get("some_measure_name").attrs.lock_count == 1
        mock_factory.assert_called_once_with(
            Path("some_fake_path/measures/some_measure_name/some_measure_name.toml")
        )