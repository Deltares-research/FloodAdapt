import os
from pathlib import Path
from typing import Any, Union
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.object_model.interface.objectModel import IDbsObject
from flood_adapt.object_model.scenario import Scenario

### Some dummy classes to be used in the tests


class DummyProjectionModel:
    name: str = "dummy_projection_name"
    description: str = "dummy_description"


class DummyProjectionObject(IDbsObject):
    attrs: DummyProjectionModel = DummyProjectionModel()

    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        return DummyProjectionObject()

    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        return DummyProjectionObject()

    def save(self, filepath: Union[str, os.PathLike]):
        """save object attributes to a toml file"""
        pass


class DummyScenarioModel:
    name: str = "dummy_event_name"
    event: str = "dont_care"
    projection: str = "dummy_projection_name"
    strategy: str = "dont_care"


class DummyScenarioObject(IDbsObject):
    attrs: DummyScenarioModel = DummyScenarioModel()

    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        return DummyScenarioObject()

    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        return DummyScenarioObject()

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
    mock_database_object.site = MagicMock()
    mock_database_object.site.attrs.standard_objects = MagicMock()
    mock_database_object.site.attrs.standard_objects.projections = []
    mock_database_object.scenarios = MagicMock()
    mock_database_object.scenarios.list_objects.return_value = {
        "path": ["some_fake_path/dummy_name"]
    }
    return mock_database_object


### End of fixtures


### Tests
class TestDbsProjections:

    def test_checkStandardProjection(self, mock_database_object):
        """Test check_standard_objects when projection is a standard projection."""

        # Arrange
        dbs_projection = DbsProjection(mock_database_object)
        dbs_projection._object_model_class = DummyProjectionObject

        # Act
        result = dbs_projection._check_standard_objects("dummy_projection_name")

        # Assert
        assert result == False

    def test_checkStandardProjection_standardProjection(self, mock_database_object):
        """Test check_standard_objects when projection is a standard projection."""

        # Arrange
        mock_database_object.site.attrs.standard_objects.projections = [
            "dummy_projection_name"
        ]
        dbs_projection = DbsProjection(mock_database_object)
        dbs_projection._object_model_class = DummyProjectionObject

        # Act
        result = dbs_projection._check_standard_objects("dummy_projection_name")

        # Assert
        assert result == True

    @patch.object(
        Scenario,
        "load_file",
        return_value=DummyScenarioObject(),
    )
    def test_checkHigherLevelUsage_noHigherLevelUsage(
        self, patch_load_scenario, mock_database_object
    ):
        """Test check_higher_level_usage when there is no higher level usage

        Patches:
        - Scenario.load_file: return DummyScenarioObject()
        """

        # Arrange
        dbs_projection = DbsProjection(mock_database_object)
        dbs_projection._object_model_class = DummyProjectionObject

        # Act
        result = dbs_projection.check_higher_level_usage("random_projection_name")

        # Assert
        assert result == []
        assert patch_load_scenario.call_count == 1

    @patch.object(
        Scenario,
        "load_file",
        return_value=DummyScenarioObject(),
    )
    def test_checkHigherLevelUsage_higherLevelUsage(
        self, patch_load_scenario, mock_database_object
    ):
        """Test check_higher_level_usage when there is higher level usage

        Patches:
        - Scenario.load_file: return DummyScenarioObject()
        """

        # Arrange
        dbs_projection = DbsProjection(mock_database_object)
        dbs_projection._object_model_class = DummyProjectionObject

        # Act
        result = dbs_projection.check_higher_level_usage("dummy_projection_name")

        # Assert
        assert result == ["dummy_event_name"]
        assert patch_load_scenario.call_count == 1