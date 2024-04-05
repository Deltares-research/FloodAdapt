import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, validator


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario"""

    name: str
    description: Optional[str] = ""
    lock_count: int = 0
    event: str
    projection: str
    strategy: str

    @validator("lock_count")
    def validate_lock_count(cls, lock_count: int) -> int:
        """Validate lock_count"""
        if lock_count < 0:
            raise ValueError("lock_count must be a positive integer")
        return lock_count


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
    def run(self) -> None: ...
