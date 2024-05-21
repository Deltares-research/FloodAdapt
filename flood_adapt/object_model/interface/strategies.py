from abc import ABC, abstractmethod
from typing import Union

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.object_classes.measure.hazard_measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)


class IStrategy(ABC):

    @abstractmethod
    def get_measures(self) -> list[Union[ImpactMeasure, HazardMeasure]]: ...

    @abstractmethod
    def get_hazard_strategy(self) -> HazardStrategy: ...

    @abstractmethod
    def get_impact_strategy(self, validate=False) -> ImpactStrategy: ...

