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
        """ Returns the object of the type of the database with the given name.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        ObjectModel
            object of the type of the spedified object model
        """
        pass

    @abstractmethod
    def set_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """
        Lock the element in the database to prevent other processes from accessing it. The object can be locked by providing either the model_object or the name.

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
        pass

    @abstractmethod
    def release_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """Releases the lock on the element in the database.

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
        pass

    @abstractmethod
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
        """Saves an object in the database.

        Parameters
        ----------
        object_model : ObjectModel
            object to be saved in the database
        overwrite : bool, optional
            whether to overwrite the object if it already exists in the database, by default False

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
        pass
