import os
import typing
from abc import ABC, abstractmethod


class IProjection(ABC):
    @abstractmethod
    def load_file(filepath: typing.Union[str, os.PathLike]):
        """create Projection from toml file"""
        ...

    @abstractmethod
    def load_dict(data: dict):
        """create Projection from object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: typing.Union[str, os.PathLike]):
        """save Projection.model to a toml file"""
