import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import pandas as pd
from pydantic import BaseModel


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    name: str
    long_name: str
    description: Optional[str] = ""
    event: str
    projection: str
    strategy: str


class IScenario(ABC):
    attrs: ScenarioModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Scenario attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """get Scenario attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Scenario attributes to a toml file"""
        ...

    @abstractmethod
    def run(self) -> None:
        ...