import shutil
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union

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

    def __init__(self, database: IDatabase):
        """
        Initialize any necessary attributes.
        """
        self.input_path = database.input_path
        self._path = self.input_path / self._folder_name
        self._database = database

    def get(self, name: str) -> ObjectModel:
        """Returns an object of the type of the database with the given name.

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

    def set_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """Locks the element in the database to prevent other processes from accessing it. The object can be locked by 
        providing either the model_object or the name. If both are provided, the model_object is used. An element can 
        be locked multiple times. For example, if 2 scenario's are running that use the same event, it should be locked 
        twice. The lock is only released when both scenario's are finished.

        Parameters
        ----------
        model_object : ObjectModel, optional
            The model_object to lock, by default None
        name : str, optional
            The name of the model_object to lock, by default None

        Raises
        ------
        ValueError
            Raise error if both model_object and name are None.
        """
        # If both model_object and name are None, raise error
        if model_object is None and name is None:
            raise ValueError("Either model_object or name must be provided.")

        # If only name is provided, get the model_object
        if model_object is None:
            model_object = self.get(name)

        # Set the lock and save the object
        model_object.attrs.lock_count += 1
        self.save(model_object, overwrite=True)

    def release_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """Releases the lock on the element in the database. The object can be unlocked by providing either the
        model_object or the name. If both are provided, the model_object is used. An element can be locked multiple
        times. For example, if 2 scenario's are running that use the same event, it should be locked twice. The lock
        is only released when both scenario's are finished.

        Parameters
        ----------
        model_object : ObjectModel, optional
            The model_object to lock, by default None
        name : str, optional
            The name of the model_object to lock, by default None

        Raises
        ------
        ValueError
            Raise error if both model_object and name are None.
        """
        # If both model_object and name are None, raise error
        if model_object is None and name is None:
            raise ValueError("Either model_object or name must be provided.")

        # If only name is provided, get the model_object
        if model_object is None:
            model_object = self.get(name)

        # Check if the object is locked
        if model_object.attrs.lock_count < 1:
            raise ValueError(
                f"'{model_object.attrs.name}' {self._type} is not locked and thus cannot be released."
            )
        
        # Release the lock and save the object
        model_object.attrs.lock_count -= 1
        self.save(model_object, overwrite=True)

    def is_locked(self, model_object: ObjectModel = None, name: str = None) -> bool:
        """Checks if the element in the database is locked.

        Parameters
        ----------
        model_object : ObjectModel, optional
            The model_object to lock, by default None
        name : str, optional
            The name of the model_object to lock, by default None

        Raises
        ------
        ValueError
            Raise error if both model_object and name are None.

        Returns
        -------
        bool
            True if the element is locked, False otherwise.
        """
        # If both model_object and name are None, raise error
        if model_object is None and name is None:
            raise ValueError("Either model_object or name must be provided.")

        # If only name is provided, get the model_object
        if model_object is None:
            model_object = self.get(name)

        # Return whether the object is locked
        return model_object.attrs.lock_count > 0

    def list_objects(self):
        """Returns a dictionary with info on the objects that currently
        exist in the database.

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
        """Copies (duplicates) an existing object, and gives it a new name.

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

        # Then a save. Checking whether the name is already in use is done in the save function
        self.save(copy_object)

        # Then save all the accompanied files
        src = self._path / old_name
        dest = self._path / new_name
        for file in src.glob("*"):
            if "toml" not in file.name:
                shutil.copy(file, dest / file.name)

    def save(self, object_model: ObjectModel, overwrite: bool = False):
        """Saves an object in the database. This only saves the toml file. If the object has a geometry, the geometry
        file should be saved separately.

        Parameters
        ----------
        object_model : ObjectModel
            object to be saved in the database
        overwrite : OverwriteMode, optional
            whether to overwrite the object if it already exists in the 
            database and if so, whether everything, only the toml or only 
            the geojson should be overwritten, by default OverwriteMode.NO_OVERWRITE

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # If you want to overwrite the object, and the object already exists, first delete it
        if overwrite and object_model.attrs.name in self.list_objects()["name"]:
            self.delete(object_model.attrs.name, only_toml=True)

        # If you don't want to overwrite, check if name is already in use
        names = self.list_objects()["name"]
        if not overwrite and object_model.attrs.name in names:
            raise ValueError(
                f"'{object_model.attrs.name}' name is already used by another {self._type}. Choose a different name"
            )

        # Make the folder and save the object
        (self._path / object_model.attrs.name).mkdir()
        object_model.save(
            self._path / object_model.attrs.name / f"{object_model.attrs.name}.toml"
        )

    def edit(self, object_model: ObjectModel):
        """Edits an already existing object in the database.

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
                f"'{object_model.attrs.name}' {self._type} does not exist. You cannot edit an object that does not exist."
            )

        # Check if it is possible to delete the object by saving with overwrite. This then
        # also covers checking whether the object is a standard object, is already used in
        # a higher level object or is locked. If any of these are the case, it cannot be deleted.
        self.save(object_model, overwrite=True)

    def delete(self, name: str):
        """Deletes an already existing object in the database.

        Parameters
        ----------
        name : str
            name of the object to be deleted

        Raises
        ------
        ValueError
            Raise error if object to be deleted is already in use.
        """

        # Check if object is a standard object
        self._check_standard_objects(name)

        # Check if object is used in a higher level object
        used_in = self._check_higher_level_usage(name)

        # Check if the object is locked by another process
        if self.is_locked(name=name):
            raise ValueError(
                f"'{name}' {self._type} is locked by another process and cannot be deleted."
            )

        # If measure is used in a strategy, raise error
        if used_in:
            raise ValueError(
                f"'{name}' measure cannot be deleted since it is already used in: {', '.join(used_in)}"
            )
        
        # Once all checks are passed, delete the object
        path = self._path / name
        shutil.rmtree(path, ignore_errors=True)

    def _check_standard_objects(self, name: str):
        """Checks if an object is a standard object.

        Parameters
        ----------
        name : str
            name of the object to be checked
        """
        # If this function is not implemented for the object type, it cannot be a standard object.
        # By default, do nothing
        pass

    def _check_higher_level_usage(self, name: str):
        """Checks if an object is used in a higher level object.

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

    def _get_object_list(self) -> dict[Path, datetime]:
        """Given an object type (e.g., measures) get a dictionary with all the toml paths
        and last modification dates that exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'path' and 'last_modification_date' info
        """
        paths = [
            Path(path / f"{path.name}.toml")
            for path in list((self.input_path / self._folder_name).iterdir())
        ]
        last_modification_date = [
            datetime.fromtimestamp(file.stat().st_mtime) for file in paths
        ]

        objects = {
            "path": paths,
            "last_modification_date": last_modification_date,
        }

        return objects
