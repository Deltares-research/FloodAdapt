import os
import shutil
from pathlib import Path
from typing import Any, Union
from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString

from flood_adapt.dbs_classes.dbs_benefit import DbsBenefit
from flood_adapt.object_model.interface.objectModel import IDbsObject
from flood_adapt.object_model.scenario import Scenario

### Some dummy classes to be used in the tests


class DummyBenefitModel:
    name: str = "dummy_benefit_name"
    description: str = "dummy_description"


class DummyBenefitObject(IDbsObject):
    attrs: DummyBenefitModel = DummyBenefitModel()
    scenarios: pd.DataFrame = pd.DataFrame(
        data={"name": ["dummy_event_name"], 
              "scenario created": ["Yes"]}
    )

    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        return DummyBenefitObject()

    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        return DummyBenefitObject()

    def save(self, filepath: Union[str, os.PathLike]):
        """save object attributes to a toml file"""
        pass


### End of dummy classes


### Fixtures
@pytest.fixture
def mock_database_object():
    mock_database_object = Mock()
    mock_database_object.input_path = Path("some_fake_path")
    mock_database_object.output_path = Path("some_fake_path")
    mock_database_object.aggr_areas = {
        "some_aggregation_area_type": gpd.GeoDataFrame(
            data={"name": ["dummy_aggregation_area"]},
            geometry=[LineString([(0, 0), (1, 1)])],
        )
    }
    mock_database_object.site = MagicMock()
    mock_database_object.site.attrs.standard_objects = MagicMock()
    mock_database_object.site.attrs.standard_objects.benefits = []
    mock_database_object.scenarios = MagicMock()
    mock_database_object.scenarios.list_objects.return_value = {
        "path": ["some_fake_path/dummy_name"]
    }
    return mock_database_object


### End of fixtures


### Tests
class TestDbsBenefits:

    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.save")
    def test_save_noOverwrite_allScenariosCreated(self, patch_template_save, mock_database_object):
        """Test save when overwrite is False."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)
        dbs_benefit._object_model_class = DummyBenefitObject

        new_object = DummyBenefitObject()
        new_object.attrs.name = "another_dummy_name"

        # Act
        dbs_benefit.save(new_object, overwrite=False)

        # Assert
        patch_template_save.assert_called_once_with(
            new_object, overwrite=False
        )

    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.save")
    def test_save_overwrite_allScenariosCreated(self, patch_template_save, mock_database_object):
        """Test save when overwrite is True."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)
        dbs_benefit._object_model_class = DummyBenefitObject

        new_object = DummyBenefitObject()
        new_object.attrs.name = "another_dummy_name"

        # Act
        dbs_benefit.save(new_object, overwrite=True)

        # Assert
        patch_template_save.assert_called_once_with(
            new_object, overwrite=True
        )

    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.save")
    def test_save_notAllScenariosCreated(self, patch_template_save, mock_database_object):
        """Test save when not all scenarios are created."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)
        dbs_benefit._object_model_class = DummyBenefitObject

        new_object = DummyBenefitObject()
        new_object.attrs.name = "another_dummy_name"
        new_object.scenarios["scenario created"] = "No"

        # Act and Assert
        with pytest.raises(ValueError) as exc_info:
            dbs_benefit.save(new_object, overwrite=False)
        assert str(exc_info.value) == "'another_dummy_name' name cannot be created before all necessary scenarios are created."

    @patch.object(Path, "exists", return_value=False)
    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.delete")
    def test_delete_noOutput(self, patch_template_delete, patch_path_exists, mock_database_object):
        """Test delete."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)

        # Act
        dbs_benefit.delete("dummy_name")

        # Assert
        patch_template_delete.assert_called_once_with("dummy_name", toml_only=False)
        patch_path_exists.assert_called_once()

    @patch.object(Path, "exists", return_value=True)
    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.delete")
    @patch.object(shutil, "rmtree")
    def test_delete_withOutput(self, patch_rmtree, patch_template_delete, patch_path_exists, mock_database_object):
        """Test delete."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)

        # Act
        dbs_benefit.delete("dummy_name")

        # Assert
        patch_template_delete.assert_called_once_with("dummy_name", toml_only=False)
        patch_path_exists.assert_called_once()
        patch_rmtree.assert_called_once_with(mock_database_object.output_path / "Benefits" / "dummy_name", ignore_errors=True)

    
    @patch.object(Path, "exists", return_value=False)
    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.edit")
    def test_edit_noOutput(self, patch_template_edit, patch_path_exists, mock_database_object):
        """Test edit."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)

        dummy_benefit = DummyBenefitObject()
        dummy_benefit.attrs.name = "dummy_name"

        # Act
        dbs_benefit.edit(dummy_benefit)

        # Assert
        patch_template_edit.assert_called_once_with(dummy_benefit)
        patch_path_exists.assert_called_once()

    @patch.object(Path, "exists", return_value=True)
    @patch("flood_adapt.dbs_classes.dbs_template.DbsTemplate.edit")
    @patch.object(shutil, "rmtree")
    def test_edit_withOutput(self, patch_rmtree, patch_template_edit, patch_path_exists, mock_database_object):
        """Test edit."""

        # Arrange
        dbs_benefit = DbsBenefit(mock_database_object)

        dummy_benefit = DummyBenefitObject()
        dummy_benefit.attrs.name = "dummy_name"

        # Act
        dbs_benefit.edit(dummy_benefit)

        # Assert
        patch_template_edit.assert_called_once_with(dummy_benefit)
        patch_path_exists.assert_called_once()
        patch_rmtree.assert_called_once_with(mock_database_object.output_path / "Benefits" / "dummy_name", ignore_errors=True)

    