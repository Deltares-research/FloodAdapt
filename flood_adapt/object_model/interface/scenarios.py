from abc import abstractmethod

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)


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

    @abstractmethod
    def equal_hazard_components(self, scenario: "IScenario") -> bool: ...
