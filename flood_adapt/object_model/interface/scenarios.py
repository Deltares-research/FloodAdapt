import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario."""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
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
        """Get Scenario attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """Get Scenario attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike], additional_files: bool = False):
        """Save Scenario attributes to a toml file, and optionally additional files."""
        ...

    @abstractmethod
    def run(self) -> None: ...
