import shutil
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Union

from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.strategies import IStrategy

ObjectModel = Union[IScenario, IEvent, IProjection, IStrategy, IMeasure, IBenefit]


class AbstractDatabase(ABC):
    def __init__(self):
        """
        Initialize any necessary attributes.
        """
        pass

    @abstractmethod
    def get(self, name: str) -> ObjectModel:
        """
        Retrieve data from the database.

        Parameters:
            name (str): The name of the data to retrieve.

        Returns:
            Any: The retrieved data.
        """
        pass

    @abstractmethod
    def list_objects(self) -> dict[str, Any]:
        """
        List data from the database.

        Returns:
            List[Any]: The listed data.
        """
        pass

    @abstractmethod
    def copy(self, old_name: str, new_name: str, new_description: str):
        """
        Copy data in the database.

        Parameters:
        ----------
        old_name : str
            name of the existing object
        new_name : str
            name of the new object
        new_description : str
            description of the new object
        """
        pass

    @abstractmethod
    def save(self, ojbect_model: ObjectModel):
        """
        Save data to the database.

        Parameters
        ----------
        ojbect_model : ObjectModel
            object to be saved in the database
        """
        pass

    @abstractmethod
    def edit(self, object_model: ObjectModel):
        """
        Edit data in the database.

        Parameters
        ----------
        object : ObjectModel
            object to be edited in the database
        """
        pass

    @abstractmethod
    def delete(self, name: str):
        """
        Delete data from the database.

        Parameters
        ----------
        name : str
            name of the object to be deleted
        """
        pass


class DbsTemplate(AbstractDatabase):
    _type = ""
    _folder_name = ""
    _object_model_class = None

    def __init__(self, database: IDatabase):
        self.input_path = database.input_path
        self._path = self.input_path / self._folder_name
        self._database = database

    def get(self, name: str) -> ObjectModel:
        """Returns an object of the type of the database.

        Parameters
        ----------
        name : str
            name of the object to be returned

        Returns
        -------
        ObjectModel
            object of the type of the database
        """
        full_path = self._path / name / f"{name}.toml"
        object_model = self._object_model_class.load_file(full_path)
        return object_model

    def list_objects(self):
        """Returns a dictionary with info on the objects that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        object_list = self._get_object_list()
        objects = [
            self._object_model_class.load_file(path) for path in object_list["path"]
        ]
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
        # First do a get
        copy_object = self.get(old_name)
        copy_object.attrs.name = new_name
        copy_object.attrs.description = new_description

        # Then a save
        self.save(copy_object)

        # Then save all the accompanied files
        src = self._path / old_name
        dest = self._path / new_name
        for file in src.glob("*"):
            if "toml" not in file.name:
                shutil.copy(file, dest / file.name)

    def save(self, ojbect_model: ObjectModel):
        """Saves an object in the database.

        Parameters
        ----------
        ojbect_model : ObjectModel
            object to be saved in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        names = self.list_objects()["name"]
        if ojbect_model.attrs.name in names:
            raise ValueError(
                f"'{ojbect_model.attrs.name}' name is already used by another {self._type}. Choose a different name"
            )
        else:
            (self._path / ojbect_model.attrs.name).mkdir()
            ojbect_model.save(
                self._path / ojbect_model.attrs.name / f"{ojbect_model.attrs.name}.toml"
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
        name = object_model.attrs.name
        # Check if it is possible to delete the object. This then also covers checking whether the
        # object is already used in a higher level object. If this is the case, it cannot be deleted.
        try:
            self.delete(name)
        except ValueError as e:
            # If not, raise error
            raise ValueError(e)
        else:
            # If correctly deleted, save the object
            self.save(object_model)

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

        # If measure is used in a strategy, raise error
        if used_in:
            raise ValueError(
                f"'{name}' measure cannot be deleted since it is already used in: {', '.join(used_in)}"
            )
        else:
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

    def _get_object_list(self) -> dict[str, Any]:
        """Given an object type (e.g., measures) get a dictionary with all the toml paths
        and last modification dates that exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'path' and 'last_modification_date' info
        """
        paths = [
            path / f"{path.name}.toml"
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
