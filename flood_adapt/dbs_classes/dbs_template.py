import shutil
from datetime import datetime
from pathlib import Path
from typing import Union

from flood_adapt.dbs_classes.dbs_interface import AbstractDatabaseElement
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.strategies import IStrategy

ObjectModel = Union[IScenario, IEvent, IProjection, IStrategy, IMeasure, IBenefit]


class DbsTemplate(AbstractDatabaseElement):
    _type = ""
    _folder_name = ""
    _object_model_class = None
    _path = None
    _database = None

    def __init__(self, database: IDatabase):
        """Initialize any necessary attributes."""
        self.input_path = database.input_path
        self._path = self.input_path / self._folder_name
        self._database = database

    def get(self, name: str) -> ObjectModel:
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
        full_path = self._path / name / f"{name}.toml"

        # Check if the object exists
        if not Path(full_path).is_file():
            raise ValueError(f"{self._type.capitalize()} '{name}' does not exist.")

        # Load and return the object
        object_model = self._object_model_class.load_file(full_path)
        return object_model

    def list_objects(self):
        """Return a dictionary with info on the objects that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info, as well as the objects themselves
        """
        # Check if all objects exist
        object_list = self._get_object_list()
        if not all(Path(path).is_file() for path in object_list["path"]):
            raise ValueError(
                f"Error in {self._type} database. Some {self._type} are missing from the database."
            )

        # Load all objects
        objects = [
            self._object_model_class.load_file(path) for path in object_list["path"]
        ]

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
            raise ValueError(f"'{old_name}' {self._type} does not exist.")

        # First do a get and change the name and description
        copy_object = self.get(old_name)
        copy_object.attrs.name = new_name
        copy_object.attrs.description = new_description

        # After changing the name and description, receate the model to re-trigger the validators
        copy_object.attrs = type(copy_object.attrs)(**copy_object.attrs.dict())

        # Then a save. Checking whether the name is already in use is done in the save function
        self.save(copy_object)

        # Then save accompanied files excluding the toml file
        src = self._path / old_name
        dest = self._path / new_name
        EXCLUDE = [".toml"]
        for file in src.glob("*"):
            if file.suffix in EXCLUDE:
                continue
            shutil.copy(file, dest / file.name)

    def save(self, object_model: ObjectModel, overwrite: bool = False):
        """Save an object in the database. This only saves the toml file. If the object also contains a geojson file, this should be saved separately.

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
                f"'{object_model.attrs.name}' name is already used by another {self._type}. Choose a different name"
            )

        # If the folder doesnt exist yet, make the folder and save the object
        if not (self._path / object_model.attrs.name).exists():
            (self._path / object_model.attrs.name).mkdir()

        object_model.save(
            self._path / object_model.attrs.name / f"{object_model.attrs.name}.toml"
        )

    def edit(self, object_model: ObjectModel):
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
                f"'{object_model.attrs.name}' {self._type} does not exist. You cannot edit an {self._type} that does not exist."
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
                f"'{name}' cannot be deleted/modified since it is a standard {self._type}."
            )

        # Check if object is used in a higher level object. If it is, raise an error
        if used_in := self.check_higher_level_usage(name):
            raise ValueError(
                f"'{name}' {self._type} cannot be deleted/modified since it is already used in: {', '.join(used_in)}"
            )

        # Once all checks are passed, delete the object
        path = self._path / name
        if toml_only:
            # Only delete the toml file
            toml_path = path / f"{name}.toml"
            if toml_path.exists():
                toml_path.unlink()
            # If the folder is empty, delete the folder
            if not list(path.iterdir()):
                path.rmdir()
        else:
            # Delete the entire folder
            shutil.rmtree(path, ignore_errors=True)

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

    def get_database_path(self, get_input_path: bool = True) -> Path:
        """Return the path to the database.

        Parameters
        ----------
        get_input_path : bool
            whether to return the input path or the output path

        Returns
        -------
        Path
            path to the database
        """
        if get_input_path:
            return Path(self._path)
        else:
            return Path(self._database.output_path / self._folder_name)

    def _get_object_list(self) -> dict[Path, datetime]:
        """Get a dictionary with all the toml paths and last modification dates that exist in the database of the given object_type.

        Returns
        -------
        dict[str, Any]
            Includes 'path' and 'last_modification_date' info
        """
        base_path = self.input_path / self._folder_name
        directories = list(base_path.iterdir())
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
