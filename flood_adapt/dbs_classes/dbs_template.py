import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar

import tomli
import tomli_w

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.objects.object_model import Object

T_OBJECTMODEL = TypeVar("T_OBJECTMODEL", bound=Object)


class DbsTemplate(AbstractDatabaseElement[T_OBJECTMODEL]):
    display_name: str
    dir_name: str
    _object_class: type[T_OBJECTMODEL]

    def __init__(self, database: IDatabase):
        """Initialize any necessary attributes."""
        self._database = database
        self.input_path = database.input_path / self.dir_name
        self.output_path = database.output_path / self.dir_name
        self.standard_objects = []

    def get(self, name: str) -> T_OBJECTMODEL:
        """Return an object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        Object
            object of the type of the specified object model
        """
        # Make the full path to the object
        full_path = self.input_path / name / f"{name}.toml"

        # Check if the object exists
        if not Path(full_path).is_file():
            raise ValueError(f"{self.display_name}: '{name}' does not exist.")

        # Load and return the object
        return self._object_class.load_file(full_path)

    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the objects that currently exist in the database.

        Returns
        -------
        dict[str, list[Any]]
            A dictionary that contains the keys: `name`, `description`, `path`  and `last_modification_date`.
            Each key has a list of the corresponding values, where the index of the values corresponds to the same object.
        """
        return self._get_object_summary()

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
        copy_object = self.get(old_name)
        copy_object.name = new_name
        copy_object.description = new_description

        # After changing the name and description, re-trigger the validators
        copy_object.model_validate(copy_object)

        # Checking whether the new name is already in use
        self._validate_to_save(copy_object, overwrite=False)

        # Write only the toml file
        toml_path = self.input_path / new_name / f"{new_name}.toml"
        toml_path.parent.mkdir(parents=True)
        with open(toml_path, "wb") as f:
            tomli_w.dump(copy_object.model_dump(exclude_none=True), f)

        # Then copy all the accompanied files
        src = self.input_path / old_name
        dest = self.input_path / new_name

        EXCLUDE = [".spw", ".toml"]
        for file in src.glob("*"):
            if file.suffix in EXCLUDE:
                continue
            if file.is_dir():
                shutil.copytree(file, dest / file.name, dirs_exist_ok=True)
            else:
                shutil.copy2(file, dest / file.name)

    def save(
        self,
        object_model: T_OBJECTMODEL,
        overwrite: bool = False,
    ):
        """Save an object in the database and all associated files.

        This saves the toml file and any additional files attached to the object.

        Parameters
        ----------
        object_model : Object
            object to be saved in the database
        overwrite : bool, optional
            whether to overwrite the object if it already exists in the
            database, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        self._validate_to_save(object_model, overwrite=overwrite)

        # If the folder doesnt exist yet, make the folder and save the object
        if not (self.input_path / object_model.name).exists():
            (self.input_path / object_model.name).mkdir()

        # Save the object and any additional files
        object_model.save(
            self.input_path / object_model.name / f"{object_model.name}.toml",
        )

    def edit(self, object_model: T_OBJECTMODEL):
        """Edit an already existing object in the database.

        Parameters
        ----------
        object_model : Object
            object to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if the object exists
        if object_model.name not in self.summarize_objects()["name"]:
            raise ValueError(
                f"{self.display_name}: '{object_model.name}' does not exist. You cannot edit an {self.display_name.lower()} that does not exist."
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
                f"'{name}' cannot be deleted/modified since it is a standard {self.display_name}."
            )

        # Check if object is used in a higher level object. If it is, raise an error
        if used_in := self.check_higher_level_usage(name):
            raise ValueError(
                f"{self.display_name}: '{name}' cannot be deleted/modified since it is already used in: {', '.join(used_in)}"
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

    def _get_object_summary(self) -> dict[str, list[Any]]:
        """Get a dictionary with all the toml paths and last modification dates that exist in the database of the given object_type.

        Returns
        -------
        dict[str, Any]
            A dictionary that contains the keys: `name`, `description`, `path`  and `last_modification_date`.
            Each key has a list of the corresponding values, where the index of the values corresponds to the same object.
        """
        # If the toml doesnt exist, we might be in the middle of saving a new object or could be a broken object.
        # In any case, we should not list it in the database
        directories = [
            dir
            for dir in self.input_path.iterdir()
            if (dir / f"{dir.name}.toml").is_file()
        ]
        paths = [Path(dir / f"{dir.name}.toml") for dir in directories]

        names = [self._read_variable_in_toml("name", path) for path in paths]
        descriptions = [
            self._read_variable_in_toml("description", path) for path in paths
        ]

        last_modification_date = [
            datetime.fromtimestamp(file.stat().st_mtime) for file in paths
        ]

        objects = {
            "name": names,
            "description": descriptions,
            "path": paths,
            "last_modification_date": last_modification_date,
        }
        return objects

    @staticmethod
    def _read_variable_in_toml(variable_name: str, toml_path: Path) -> str:
        with open(toml_path, "rb") as f:
            data = tomli.load(f)
        return data.get(variable_name, "")

    def _validate_to_save(self, object_model: T_OBJECTMODEL, overwrite: bool) -> None:
        """Validate if the object can be saved.

        Parameters
        ----------
        object_model : Object
            object to be validated

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if the object exists
        object_exists = object_model.name in self.summarize_objects()["name"]

        # If you want to overwrite the object, and the object already exists, first delete it. If it exists and you
        # don't want to overwrite, raise an error.
        if overwrite and object_exists:
            self.delete(object_model.name, toml_only=True)
        elif not overwrite and object_exists:
            raise ValueError(
                f"'{object_model.name}' name is already used by another {self.display_name.lower()}. Choose a different name"
            )
