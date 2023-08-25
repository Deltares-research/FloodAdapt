import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel


class StrategyModel(BaseModel):
    name: str
    description: Optional[str] = ""
    measures: Optional[list[str]] = []


class IStrategy(ABC):
    attrs: StrategyModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get Strategy attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get Strategy attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Strategy attributes to a toml file"""
