import os
from abc import ABC, abstractmethod
from typing import Any, Union

from flood_adapt.object_model.models.site import SiteModel


class ISite(ABC):
    attrs: SiteModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Site attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get Site attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Site attributes to a toml file"""
