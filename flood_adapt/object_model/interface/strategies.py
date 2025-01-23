from abc import abstractmethod

from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import ObjectDir


class StrategyModel(IObjectModel):
    measures: list[str] = []


class IStrategy(IObject[StrategyModel]):
    _attrs_type = StrategyModel
    dir_name = ObjectDir.strategy
    display_name = "Strategy"

    @abstractmethod
    def get_measures(self) -> list[IMeasure]: ...

    @abstractmethod
    def get_impact_strategy(self, validate=False) -> ImpactStrategy: ...

    @abstractmethod
    def get_hazard_strategy(self) -> HazardStrategy: ...
