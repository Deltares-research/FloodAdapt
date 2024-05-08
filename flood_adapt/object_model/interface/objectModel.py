import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class DbsObjectModel(BaseModel):
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""


class IDbsObject(ABC):
    attrs: DbsObjectModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """get object attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """get object attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save object attributes to a toml file"""
        ...
