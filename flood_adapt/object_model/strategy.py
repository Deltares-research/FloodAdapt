from typing import Any

from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.measures import (
    IMeasure,
    MeasureType,
)
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    db_path,
)
from flood_adapt.object_model.interface.strategies import IStrategy, StrategyModel
from flood_adapt.object_model.measure_factory import (
    MeasureFactory,
)


class Strategy(IStrategy):
    """Strategy class that holds all the information for a specific strategy."""

    def __init__(self, data: dict[str, Any] | StrategyModel) -> None:
        super().__init__(data)
        self.impact_strategy = self.get_impact_strategy()
        self.hazard_strategy = self.get_hazard_strategy()

    def get_measures(self) -> list[IMeasure]:
        """Get the measures paths and types."""
        # Get measure paths using a database structure
        measure_paths = [
            db_path(object_dir=ObjectDir.measure, obj_name=measure) / f"{measure}.toml"
            for measure in self.attrs.measures
        ]
        return [MeasureFactory.get_measure_object(path) for path in measure_paths]

    def get_impact_strategy(self) -> ImpactStrategy:
        impact_measures = [
            measure
            for measure in self.get_measures()
            if MeasureType.is_impact(measure.attrs.type)
        ]
        return ImpactStrategy(
            measures=impact_measures,
        )

    def get_hazard_strategy(self) -> HazardStrategy:
        hazard_measures = [
            measure
            for measure in self.get_measures()
            if MeasureType.is_hazard(measure.attrs.type)
        ]
        return HazardStrategy(measures=hazard_measures)
