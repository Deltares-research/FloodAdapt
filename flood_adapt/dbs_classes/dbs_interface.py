from abc import ABC, abstractmethod
from typing import Any, Union

from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.strategies import IStrategy

ObjectModel = Union[IScenario, IEvent, IProjection, IStrategy, IMeasure, IBenefit]


class AbstractDatabaseElement(ABC):
    def __init__(self):
        """
        Initialize any necessary attributes.
        """
        pass

    @abstractmethod
    def get(self, name: str) -> ObjectModel:
        """Returns the object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        ObjectModel
            object of the type of the specified object model
        """
        pass

    @abstractmethod
    def list_objects(self) -> dict[str, Any]:
        """Returns a dictionary with info on the objects that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info, as well as the objects themselves
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def save(self, object_model: ObjectModel, overwrite: bool = False):
        """Saves an object in the database. This only saves the toml file. If the object also contains a geojson file,
        this should be saved separately.

        Parameters
        ----------
        object_model : ObjectModel
            object to be saved in the database
        overwrite : OverwriteMode, optional
            whether to overwrite the object if it already exists in the
            database, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def delete(self, name: str, toml_only: bool = False):
        """Deletes an already existing object in the database.

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
        pass
