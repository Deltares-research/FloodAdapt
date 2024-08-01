import os
from abc import abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.database_user import IDatabaseUser


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of a scenario."""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    event: str
    projection: str
    strategy: str


class IScenario(IDatabaseUser):
    attrs: ScenarioModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Scenario attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike] = None
    ):
        """Get Scenario attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Scenario attributes to a toml file."""
        ...

    @abstractmethod
    def run(self) -> None: ...
