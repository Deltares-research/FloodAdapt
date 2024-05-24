import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.interface.site import ISite, SiteModel


class Site(ISite):
    """Class for general variables of the object_model"""

    _attrs: SiteModel

    @property
    def attrs(self) -> SiteModel:
        return self._attrs
    
    @attrs.setter
    def attrs(self, value: SiteModel):
        self._attrs = value
                
    
    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Site from toml file"""

        obj = Site()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SiteModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Site()
        obj.attrs = SiteModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]) -> None:
        """write toml file from model object"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self._attrs.dict(exclude_none=True), f)
