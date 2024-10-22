from abc import abstractmethod

from flood_adapt.object_model.interface.database import (
    ObjectDir,
)
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel


class ScenarioModel(IObjectModel):
    """BaseModel describing the expected variables and data types of a scenario."""

    event: str
    projection: str
    strategy: str


class IScenario(IObject[ScenarioModel]):
    attrs: ScenarioModel
    dir_name = ObjectDir.scenario

    @abstractmethod
    def run(self) -> None: ...
