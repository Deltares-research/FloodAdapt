import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Type

from flood_adapt.dbs_classes.dbs_interface import AbstractDatabaseElement
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.object_model import IObject
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)


class DbsTemplate(AbstractDatabaseElement):
    _object_class: Type[IObject]

    def __init__(self, database: IDatabase):
        """Initialize any necessary attributes."""
        self._database = database
        self.input_path = db_path(
            top_level_dir=TopLevelDir.input, object_dir=self._object_class.dir_name
        )
        self.output_path = db_path(
            top_level_dir=TopLevelDir.output, object_dir=self._object_class.dir_name
        )
        self.standard_objects = []

    def get(self, name: str) -> IObject:
        """Return an object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        ObjectModel
            object of the type of the specified object model
        """
        # Make the full path to the object
        full_path = self.input_path / name / f"{name}.toml"
        full_path = self.input_path / name / f"{name}.toml"

        # Check if the object exists
        if not Path(full_path).is_file():
            raise ValueError(
                f"{self._object_class.class_name} '{name}' does not exist."
            )

        # Load and return the object
        object_model = self._object_class.load_file(full_path)
        return object_model

    def list_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the objects that currently exist in the database.

        Returns
        -------
        dict[str, list[Any]]
            A dictionary that contains the keys: `name`, 'path', 'last_modification_date', 'description', 'objects'
            Each key has a list of the corresponding values, where the index of the values corresponds to the same object.
        """
        # Check if all objects exist
        object_list = self._get_object_list()
        if not all(Path(path).is_file() for path in object_list["path"]):
            raise ValueError(
                f"Error in {self._object_class.class_name} database. Some {self._object_class.class_name} are missing from the database."
            )

        # Load all objects
        objects = [self._object_class.load_file(path) for path in object_list["path"]]

        # From the loaded objects, get the name and description and add them to the object_list
        object_list["name"] = [obj.attrs.name for obj in objects]
        object_list["description"] = [obj.attrs.description for obj in objects]
        object_list["objects"] = objects
        return object_list

    def copy(self, old_name: str, new_name: str, new_description: str):
        """Copy (duplicate) an existing object, and give it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing measure
        new_name : str
            name of the new measure
        new_description : str
            description of the new measure
        """
        # Check if the provided old_name is valid
        if old_name not in self.list_objects()["name"]:
            raise ValueError(
                f"'{old_name}' {self._object_class.class_name} does not exist."
            )

        # First do a get and change the name and description
        copy_object = self.get(old_name)
        copy_object.attrs.name = new_name
        copy_object.attrs.description = new_description

        # After changing the name and description, receate the model to re-trigger the validators
        copy_object.attrs = type(copy_object.attrs)(**copy_object.attrs.model_dump())

        EXCLUDE_SUFFIX = [".spw"]
        try:
            # Copy the folder
            shutil.copytree(
                self.input_path / old_name,
                self.input_path / new_name,
                ignore=shutil.ignore_patterns(*EXCLUDE_SUFFIX),
            )

            # Rename the toml file to not raise in the name check
            os.rename(
                self.input_path / new_name / f"{old_name}.toml",
                self.input_path / new_name / f"{new_name}.toml",
            )

            # Check new name is valid and update toml file
            self.save(copy_object, overwrite=True)
        except:
            # If an error occurs, delete the folder and raise the error
            shutil.rmtree(self.input_path / new_name, ignore_errors=True)
            raise

    def save(
        self,
        object_model: IObject,
        overwrite: bool = False,
    ):
        """Save an object in the database and all associated files.

        This saves the toml file and any additional files attached to the object.

        Parameters
        ----------
        object_model : ObjectModel
            object to be saved in the database
        overwrite : bool, optional
            whether to overwrite the object if it already exists in the
            database, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        object_exists = object_model.attrs.name in self.list_objects()["name"]

        # If you want to overwrite the object, and the object already exists, first delete it. If it exists and you
        # don't want to overwrite, raise an error.
        if overwrite and object_exists:
            self.delete(object_model.attrs.name, toml_only=True)
        elif not overwrite and object_exists:
            raise ValueError(
                f"'{object_model.attrs.name}' name is already used by another {self._object_class.class_name}. Choose a different name"
            )

        # If the folder doesnt exist yet, make the folder and save the object
        if not (self.input_path / object_model.attrs.name).exists():
            (self.input_path / object_model.attrs.name).mkdir()

        # Save the object and any additional files
        object_model.save(
            self.input_path
            / object_model.attrs.name
            / f"{object_model.attrs.name}.toml",
        )

    def edit(self, object_model: IObject):
        """Edit an already existing object in the database.

        Parameters
        ----------
        object : ObjectModel
            object to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if the object exists
        if object_model.attrs.name not in self.list_objects()["name"]:
            raise ValueError(
                f"'{object_model.attrs.name}' {self._object_class.class_name} does not exist. You cannot edit an {self._object_class.class_name} that does not exist."
            )

        # Check if it is possible to delete the object by saving with overwrite. This then
        # also covers checking whether the object is a standard object, is already used in
        # a higher level object. If any of these are the case, it cannot be deleted.
        self.save(object_model, overwrite=True)

    def delete(self, name: str, toml_only: bool = False):
        """Delete an already existing object in the database.

        Parameters
        ----------
        name : str
            name of the object to be deleted
        toml_only : bool, optional
            whether to only delete the toml file or the entire folder. If the folder is empty after deleting the toml,
            it will always be deleted. By default False

        Raises
        ------
        ValueError
            Raise error if object to be deleted is already in use.
        """
        # Check if the object is a standard object. If it is, raise an error
        if self._check_standard_objects(name):
            raise ValueError(
                f"'{name}' cannot be deleted/modified since it is a standard {self._object_class.class_name}."
            )

        # Check if object is used in a higher level object. If it is, raise an error
        if used_in := self.check_higher_level_usage(name):
            raise ValueError(
                f"'{name}' {self._object_class.class_name} cannot be deleted/modified since it is already used in: {', '.join(used_in)}"
            )

        # Once all checks are passed, delete the object
        toml_path = self.input_path / name / f"{name}.toml"
        if toml_only:
            # Only delete the toml file
            toml_path.unlink(missing_ok=True)
            # If the folder is empty, delete the folder
            if not list(toml_path.parent.iterdir()):
                toml_path.parent.rmdir()
        else:
            # Delete the entire folder
            shutil.rmtree(toml_path.parent, ignore_errors=True)
            if (self.output_path / name).exists():
                shutil.rmtree(self.output_path / name, ignore_errors=True)

    def _check_standard_objects(self, name: str) -> bool:
        """Check if an object is a standard object.

        Parameters
        ----------
        name : str
            name of the object to be checked

        Returns
        -------
        bool
            True if the object is a standard object, False otherwise
        """
        # If this function is not implemented for the object type, it cannot be a standard object.
        # By default, it is not a standard object.
        return False

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Check if an object is used in a higher level object.

        Parameters
        ----------
        name : str
            name of the object to be checked

        Returns
        -------
        list[str]
            list of higher level objects that use the object
        """
        # If this function is not implemented for the object type, it cannot be used in a higher
        # level object. By default, return an empty list
        return []

    def _get_object_list(self) -> dict[str, list[Any]]:
        """Get a dictionary with all the toml paths and last modification dates that exist in the database of the given object_type.

        Returns
        -------
        dict[str, Any]
            A dictionary that contains the keys: `name` to 'path' and 'last_modification_date'
            Each key has a list of the corresponding values, where the index of the values corresponds to the same object.
        """
        directories = [self.input_path / d for d in os.listdir(self.input_path)]
        paths = [Path(dir / f"{dir.name}.toml") for dir in directories]
        names = [dir.name for dir in directories]
        last_modification_date = [
            datetime.fromtimestamp(file.stat().st_mtime) for file in paths
        ]

        objects = {
            "name": names,
            "path": paths,
            "last_modification_date": last_modification_date,
        }

        return objects
