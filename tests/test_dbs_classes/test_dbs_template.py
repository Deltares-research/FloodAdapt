import datetime
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Union
from unittest.mock import Mock, patch

import pytest
import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.interface.objectModel import IDbsObject

### Some dummy classes to be used in the tests


class DummyObjectModel(BaseModel):
    name: str = "dummy_name"
    description: str = "dummy_description"


class DummyObject(IDbsObject):
    attrs: DummyObjectModel = DummyObjectModel()
    database_input_path = Path("some_fake_path")

    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        dummy_object = DummyObject()
        dummy_object.attrs = DummyObjectModel.parse_obj(toml)
        dummy_object.database_input_path = Path(filepath).parents[1]
        return dummy_object

    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        dummy_object = DummyObject()
        dummy_object.attrs = DummyObjectModel.parse_obj(data)
        dummy_object.database_input_path = database_input_path
        return dummy_object

    def save(self, filepath: Union[str, os.PathLike]):
        """save object attributes to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)


### End of dummy classes


### Fixtures
@pytest.fixture
def mock_database_object():
    temp_dir = tempfile.mkdtemp()

    dummy_model = DummyObject()
    temp_file = Path(temp_dir) / "dummy_name" / "dummy_name.toml"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    dummy_model.save(temp_file)

    mock_database_object = Mock()
    mock_database_object.input_path = Path(temp_dir)

    yield mock_database_object

    shutil.rmtree(temp_dir)


### End of fixtures

### Mocks for internal functions


@pytest.fixture
def patch_delete(mock_database_object):
    # Skip all fuzzy stuff but only delete the file
    shutil.rmtree(mock_database_object.input_path / "dummy_name")


### End of mocks for internal functions


### Tests
class TestDbsObject:

    def test_getObject_fileFound(self, mock_database_object):
        """Test that the get_object method returns the correct object object when the file is found."""

        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        # Act
        object = database_template_class.get("dummy_name")

        # Assert
        assert object.attrs.name == "dummy_name"
        assert object.attrs.description == "dummy_description"

    def test_getObject_fileNotFound(self, mock_database_object):
        """Test that the get_object method raises a ValueError when the file is not found.

        Patches:
        - Path.is_file: to return False
        """

        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        os.remove(mock_database_object.input_path / "dummy_name" / "dummy_name.toml")

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.get("dummy_name")
        assert " 'dummy_name' does not exist." in str(excinfo.value)

    @patch.object(
        Path,
        "stat",
        return_value=os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0)),
    )
    def test_getObjectList_happyFlow(self, patch_stat, mock_database_object):
        """Test that the list_objects method returns a dictionary with the correct information.

        Patches:
        - Path.stat: to return the mock path stats. Otherwise, it will give different results on different systems.
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        object_path = (
            Path(database_template_class.input_path) / "dummy_name" / "dummy_name.toml"
        )

        # Act
        objects = database_template_class._get_object_list()

        # Assert
        assert objects["path"] == [object_path]
        assert objects["last_modification_date"] == [
            datetime.datetime(1970, 1, 1, 1, 0)
        ]

    def test_getObjectList_noObjects(self, mock_database_object):
        """Test that the list_objects method returns an empty dictionary if no objects are found in the database."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        shutil.rmtree(mock_database_object.input_path / "dummy_name")

        # Act
        objects = database_template_class._get_object_list()

        # Assert
        assert objects == {"path": [], "last_modification_date": []}

    @patch.object(
        Path,
        "stat",
        return_value=os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0)),
    )
    def test_listObjects_happyFlow(self, patch_stat, mock_database_object):
        """Test that the list_objects method returns a dictionary with the correct information.

        Patches:
        - Path.stat: to return the mock path stats. Otherwise, it will give different results on different systems.
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        object_path = (
            Path(database_template_class.input_path) / "dummy_name" / "dummy_name.toml"
        )

        # Act
        # Using this patch globaly breaks checking the call count of the patch
        objects = database_template_class.list_objects()

        # Assert
        assert objects["path"] == [object_path]
        assert objects["last_modification_date"] == [
            datetime.datetime(1970, 1, 1, 1, 0)
        ]
        assert objects["name"] == ["dummy_name"]
        assert objects["description"] == ["dummy_description"]
        assert type(objects["objects"][0]) == DummyObject
        assert type(objects["objects"][0].attrs) == DummyObjectModel
        assert objects["objects"][0].attrs.name == "dummy_name"
        assert objects["objects"][0].attrs.description == "dummy_description"
        assert objects["objects"][0].database_input_path == Path(
            database_template_class.input_path
        )

    def test_listObjects_noObjects(self, mock_database_object):
        """Test that the list_objects method returns an empty dictionary if no objects are found in the database."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        shutil.rmtree(mock_database_object.input_path / "dummy_name")

        # Act
        objects = database_template_class.list_objects()

        # Assert
        assert objects == {
            "path": [],
            "last_modification_date": [],
            "name": [],
            "description": [],
            "objects": [],
        }

    @patch.object(
        Path,
        "stat",
        return_value=os.stat_result((0, 0, 0, 0, 0, 0, 0, time.time(), 0, 0)),
    )
    def test_listObjects_fileNotFound(
        self,
        patch_stat,
        mock_database_object,
    ):
        """Test that the list_objects method raises a FileNotFoundError when a file is not found.

        Patches:
        - Path.stat: to return the mock path stats
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        os.remove(mock_database_object.input_path / "dummy_name" / "dummy_name.toml")

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.list_objects()
        assert "Error in  database. Some  are missing from the database." in str(
            excinfo.value
        )

    @patch.object(DbsTemplate, "check_higher_level_usage", return_value=[])
    @patch.object(DbsTemplate, "_check_standard_objects", return_value=False)
    def test_deleteObject_onlyToml(
        self,
        patch_is_no_standard_object,
        patch_not_used_in_higher_level,
        mock_database_object,
    ):
        """Test that the delete_object method deletes the object from the database.

        Patches:
        - DbsTemplate._check_standard_objects: to return False
        - DbsTemplate.check_higher_level_usage: to return an empty list
        """

        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        object_path = Path("some_fake_path/dummy_name/dummy_name.toml")

        # Act
        database_template_class.delete("dummy_name", toml_only=True)

        # Assert
        assert not object_path.exists()
        assert patch_is_no_standard_object.call_count == 1
        patch_is_no_standard_object.assert_called_once_with("dummy_name")
        assert patch_not_used_in_higher_level.call_count == 1
        patch_not_used_in_higher_level.assert_called_once_with("dummy_name")

    @patch.object(DbsTemplate, "check_higher_level_usage", return_value=[])
    @patch.object(DbsTemplate, "_check_standard_objects", return_value=False)
    def test_deleteObject_entireFolder(
        self,
        patch_is_no_standard_object,
        patch_not_used_in_higher_level,
        mock_database_object,
    ):
        """Test that the delete_object method deletes the object from the database.

        Patches:
        - DbsTemplate._check_standard_objects: to return False
        - DbsTemplate.check_higher_level_usage: to return an empty list
        """

        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject
        object_path = Path("some_fake_path/dummy_name/dummy_name.toml")

        # Act
        database_template_class.delete("dummy_name", toml_only=False)

        # Assert
        assert not object_path.exists()
        assert not object_path.parent.exists()
        assert patch_is_no_standard_object.call_count == 1
        patch_is_no_standard_object.assert_called_once_with("dummy_name")
        assert patch_not_used_in_higher_level.call_count == 1
        patch_not_used_in_higher_level.assert_called_once_with("dummy_name")

    @patch.object(
        DbsTemplate,
        "check_higher_level_usage",
        return_value=["some_higher_level_object"],
    )
    @patch.object(DbsTemplate, "_check_standard_objects", return_value=False)
    def test_deleteObject_usedInHigherLevel(
        self,
        patch_is_no_standard_object,
        patch_higher_level_usage,
        mock_database_object,
    ):
        """Test that the delete_object method raises a ValueError when the object is used in a higher level object.

        Patches:
        - DbsTemplate._check_standard_objects: to return False
        - DbsTemplate.check_higher_level_usage: to return a list with a higher level object
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.delete("dummy_name", toml_only=False)
        assert (
            "'dummy_name'  cannot be deleted/modified since it is already used in: some_higher_level_object"
            in str(excinfo.value)
        )
        assert patch_higher_level_usage.call_count == 1
        patch_higher_level_usage.assert_called_once_with("dummy_name")

    @patch.object(DbsTemplate, "_check_standard_objects", return_value=True)
    @patch.object(DbsTemplate, "check_higher_level_usage", return_value=[])
    def test_deleteObject_standardObject(
        self, patch_no_higher_level_uses, patch_is_standard_object, mock_database_object
    ):
        """Test that the delete_object method raises a ValueError when the object is a standard object.

        Patches:
        - DbsTemplate._check_standard_objects: to return True
        - DbsTemplate.check_higher_level_usage: to return an empty list
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.delete("dummy_name", toml_only=False)
        assert (
            "'dummy_name' cannot be deleted/modified since it is a standard ."
            in str(excinfo.value)
        )
        assert patch_is_standard_object.call_count == 1
        patch_is_standard_object.assert_called_once_with("dummy_name")

    def test_saveObject_noOverwrite(
        self,
        mock_database_object,
    ):
        """Test that the save_object method saves the object to a file."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = DummyObject()
        new_object.attrs.name = "another_dummy_name"

        # Act
        database_template_class.save(new_object, overwrite=False)

        # Assert
        with open(
            database_template_class.input_path
            / "another_dummy_name"
            / "another_dummy_name.toml",
            mode="rb",
        ) as fp:

            result = tomli.load(fp)
        assert result["name"] == "another_dummy_name"
        assert result["description"] == "dummy_description"

    def test_saveObject_overwrite(self, mock_database_object):
        """Test that the save_object method saves the object to a file.

        Patches:
        """
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = (
            DummyObject()
        )  # Keep the existing name, otherwise it cannot overwrite
        new_object.attrs.description = "new_description"

        # Act
        database_template_class.save(new_object, overwrite=True)

        # Assert
        with open(
            database_template_class.input_path / "dummy_name" / "dummy_name.toml",
            mode="rb",
        ) as fp:
            result = tomli.load(fp)

        assert result["name"] == "dummy_name"
        assert result["description"] == "new_description"

    def test_saveObject_nameInUse_noOverwrite(self, mock_database_object):
        """Test that the save_object method raises a ValueError when the name is already in use and overwrite is False."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = DummyObject()

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.save(new_object, overwrite=False)
        assert (
            "'dummy_name' name is already used by another . Choose a different name"
            in str(excinfo.value)
        )

    def test_saveObject_nameNotInUse_overwrite(
        self,
        mock_database_object,
    ):
        """Test that the save_object method still saves the object when the name is not in use and overwrite is True."""

        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = DummyObject()
        new_object.attrs.name = "another_dummy_name"
        new_object.attrs.description = "dummy_description"

        # Act
        database_template_class.save(new_object, overwrite=True)

        # Assert
        with open(
            database_template_class.input_path
            / "another_dummy_name"
            / "another_dummy_name.toml",
            mode="rb",
        ) as fp:
            result = tomli.load(fp)
        assert result["name"] == "another_dummy_name"
        assert result["description"] == "dummy_description"

    def test_editObject_happyFlow(self, mock_database_object):
        """Test that the edit_object method edits the object in the database."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = DummyObject()
        new_object.attrs.name = "dummy_name"
        new_object.attrs.description = "new_description"

        # Act
        database_template_class.edit(new_object)

        # Assert
        with open(
            database_template_class.input_path / "dummy_name" / "dummy_name.toml",
            mode="rb",
        ) as fp:
            result = tomli.load(fp)

        assert result["name"] == "dummy_name"
        assert result["description"] == "new_description"

    def test_editObject_objectNotFound(self, mock_database_object):
        """Test that the edit_object method raises a ValueError when the object is not found in the database."""
        # Arrange
        database_template_class = DbsTemplate(mock_database_object)
        database_template_class._object_model_class = DummyObject

        new_object = DummyObject()
        new_object.attrs.name = "another_dummy_name"

        # Act
        with pytest.raises(ValueError) as excinfo:
            database_template_class.edit(new_object)
        assert (
            "'another_dummy_name'  does not exist. You cannot edit an  that does not exist."
            in str(excinfo.value)
        )
