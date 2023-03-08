import os
import typing
from abc import ABC, abstractmethod


class IElevate(ABC):
    @abstractmethod
    def load(self, config_file: typing.Union[str, os.PathLike]):
        """loads the object properties from a configuration file"""
        ...

    @abstractmethod
    def get_object_ids(self) -> list[any]:
        """get the object ids of the properties affected by the implemented measure"""
        ...
