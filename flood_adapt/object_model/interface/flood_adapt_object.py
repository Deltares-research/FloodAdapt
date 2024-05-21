from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class IFAObject(ABC):
    """This is a template class for FloodAdapt objects"""

    _attrs: BaseModel
    _type: str

    @property
    @abstractmethod
    def attrs(self) -> BaseModel:
        """Get the attributes of the object

        Returns
        -------
        BaseModel
            The attributes of the object
        """
        pass

    @classmethod
    @abstractmethod
    def load_dict(cls, data: dict[str, Any]):
        """Get a FloodAdapt object from a dict containing the object's attributes
        
        Parameters
        ----------
        cls : Type[IFAObject]
            The class of the object to create
        data : dict[str, Any]
            The data to create the object from

        Returns
        -------
        IFAObject
            The created object
        """
        pass

