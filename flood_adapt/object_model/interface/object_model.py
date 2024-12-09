import logging
import os
from abc import ABC
from pathlib import Path
from typing import Any, Generic, Type, TypeVar

import tomli
import tomli_w
from pydantic import BaseModel, Field

from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)


class IObjectModel(BaseModel):
    """Base class for object models.

    Attributes
    ----------
    name : str
        Name of the object.
    description : str (optional)
        Description of the object.
    """

    name: str = Field(
        ...,
        description="Name of the object.",
        min_length=1,
        pattern='^[^<>:"/\\\\|?* ]*$',
    )
    description: str = Field(default="", description="Description of the object.")


# Add typevars so that type checking works correctly
T_OBJECT = TypeVar("T_OBJECT", bound="IObject")
T_OBJECTMODEL = TypeVar("T_OBJECTMODEL", bound="IObjectModel")


class IObject(ABC, Generic[T_OBJECTMODEL]):
    """Base class for all FloodAdapt objects.

    Contains methods for loading and saving objects to disk.

    Class Attributes
    ----------------
    dir_name : ObjectDir
        The directory name of the object used in the database.
    display_name : str
        The display name of the object used in the UI.

    Instance Properties
    -------------------
    attrs : ObjectModel
        The object model containing the data for the object. It should be a subclass of IObjectModel.

    Methods
    -------
    __init__(data: dict[str, Any] | IObjectModel) -> None
        Initialize the object.
    load_file(file_path: Path | str | os.PathLike) -> IObject
        Load object from file.
    load_dict(data: dict[str, Any]) -> IObject
        Load object from dictionary.
    save_additional(output_dir: Path | str | os.PathLike) -> None
        Save additional files to database if the object has any and update attrs to reflect the change in file location.
    save(toml_path: Path | str | os.PathLike) -> None
        Save object to disk, including any additional files.
    """

    _attrs_type: Type[T_OBJECTMODEL]

    dir_name: ObjectDir
    display_name: str

    _logger: logging.Logger

    def __init__(self, data: dict[str, Any] | T_OBJECTMODEL) -> None:
        """Validate the object model passed in as 'data' and assign it to self.attrs."""
        if isinstance(data, self.__class__._attrs_type):
            self._attrs = data
        elif isinstance(data, dict):
            self._attrs = self.__class__._attrs_type.model_validate(data)
        else:
            raise TypeError(f"Expected {self._attrs_type} or dict, got {type(data)}")

    @property
    def attrs(self) -> T_OBJECTMODEL:
        """Return the object model."""
        return self._attrs

    @attrs.setter
    def attrs(self, value: T_OBJECTMODEL) -> None:
        """Set the object model."""
        if isinstance(value, self._attrs_type):
            self._attrs = value
        elif isinstance(value, dict):
            self._attrs = self._attrs_type.model_validate(value)
        else:
            raise TypeError(f"Expected {self._attrs_type} or dict, got {type(value)}")

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Return the logger for the object."""
        if not hasattr(cls, "_logger") or cls._logger is None:
            cls._logger = FloodAdaptLogging.getLogger(cls.__name__)
        return cls._logger

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for the object."""
        return self.get_logger()

    @classmethod
    def load_file(cls: Type[T_OBJECT], file_path: Path | str | os.PathLike) -> T_OBJECT:
        """Load object from file."""
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        return cls.load_dict(toml)

    @classmethod
    def load_dict(
        cls: Type[T_OBJECT], data: dict[str, Any] | T_OBJECTMODEL
    ) -> T_OBJECT:
        """Load object from dictionary."""
        return cls(data)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """
        Save additional files to database if the object has any and update attrs to reflect the change in file location.

        This method should be overridden if the object has additional files.
        """
        pass

    def save(self, toml_path: Path | str | os.PathLike) -> None:
        """Save object to disk, including any additional files."""
        self.save_additional(output_dir=Path(toml_path).parent)
        with open(toml_path, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    def __eq__(self, other) -> bool:
        if not isinstance(other, type(self)):
            # don't attempt to compare against unrelated types
            return False
        attrs_1 = self.attrs.model_dump(exclude={"name", "description"})
        attrs_2 = other.attrs.model_dump(exclude={"name", "description"})
        return attrs_1 == attrs_2
