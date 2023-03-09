import os
import typing
from abc import ABC, abstractmethod


class IElevate(ABC):
    @abstractmethod
    def get_object_ids(self) -> list[any]:
        """get the object ids of the properties affected by the implemented measure"""
        ...

    @abstractmethod
    def load_file(filepath: typing.Union[str, os.PathLike]):
        """create Elevate from toml file"""
        ...

    @abstractmethod
    def load_dict(data: dict):
        """create Elevate from object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: typing.Union[str, os.PathLike]):
        """save Elavate.model to a toml file"""
        ...


class IFloodwall(ABC):
    @abstractmethod
    def load_file(filepath: typing.Union[str, os.PathLike]):
        """create Elevate from toml file"""
        ...

    @abstractmethod
    def load_dict(data: dict):
        """create Elevate from object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: typing.Union[str, os.PathLike]):
        """save Elavate.model to a toml file"""
        ...
