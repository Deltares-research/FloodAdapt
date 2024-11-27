from abc import abstractmethod

from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import ObjectDir
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.strategies import IStrategy


class ScenarioModel(IObjectModel):
    """BaseModel describing the expected variables and data types of a scenario."""

    event: str
    projection: str
    strategy: str


class IScenario(IObject[ScenarioModel]):
    _attrs_type = ScenarioModel
    dir_name = ObjectDir.scenario
    display_name = "Scenario"

    @abstractmethod
    def run(self) -> None: ...

    @abstractmethod
    def equal_hazard_components(self, other: "IScenario") -> bool: ...

    @abstractmethod
    def get_event(self) -> IEvent: ...

    @abstractmethod
    def get_projection(self) -> IProjection: ...

    @abstractmethod
    def get_strategy(self) -> IStrategy: ...
