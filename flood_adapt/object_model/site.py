import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.interface.site import ISite, SiteModel


class Site(ISite):
    """Class for general variables of the object_model"""

    attrs: SiteModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Site from toml file"""

        obj = Site()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = SiteModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Site()
        obj.attrs = SiteModel.parse_obj(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]) -> None:
        """write toml file from model object"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
