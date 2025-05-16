from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from flood_adapt.objects.object_model import Object

T_OBJECT_MODEL = TypeVar("T_OBJECT_MODEL", bound=Object)


class AbstractDatabaseElement(ABC, Generic[T_OBJECT_MODEL]):
    input_path: Path
    output_path: Path

    @abstractmethod
    def __init__(self):
        """Abstract class for database elements."""
        pass

    @abstractmethod
    def get(self, name: str) -> T_OBJECT_MODEL:
        """Return the object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        IObject
            object of the type of the specified object model
        """
        pass

    @abstractmethod
    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the objects that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info, as well as the objects themselves
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def save(
        self,
        object_model: T_OBJECT_MODEL,
        overwrite: bool = False,
    ):
        """Save an object in the database.

        This only saves the toml file. If the object also contains a geojson file, this should be saved separately.

        Parameters
        ----------
        object_model : Object
            object to be saved in the database
        overwrite : bool, optional
            whether to overwrite the object if it already exists in the
            database, by default False
        toml_only : bool, optional
            whether to only save the toml file or all associated data. By default, save everything

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        pass

    @abstractmethod
    def edit(self, object_model: T_OBJECT_MODEL):
        """Edits an already existing object in the database.

        Parameters
        ----------
        object : IObject
            object to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass
