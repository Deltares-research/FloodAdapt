from typing import Any

from pydantic import BaseModel

from flood_adapt.object_model.interface.flood_adapt_object import (
    IFAObject,
)


class FAObject(IFAObject):
    """This is a template class for FloodAdapt objects"""

    _attrs = BaseModel
    _type = ""

    @property
    def attrs(self) -> BaseModel:
        """Get the attributes of the object

        Returns
        -------
        BaseModel
            The attributes of the object
        """
        return self._attrs

    @classmethod
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
        obj = cls()
        obj.attrs = obj.attrs.parse_obj(data)
        return obj

