from typing import Any, Union

from flood_adapt.dbs_classes.path_builder import ObjectDir, db_path
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.interface.measures import HazardType, ImpactType
from flood_adapt.object_model.interface.strategies import IStrategy, StrategyModel
from flood_adapt.object_model.measure_factory import (
    MeasureFactory,
)


class Strategy(IStrategy):
    """Strategy class that holds all the information for a specific strategy."""

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, StrategyModel):
            self.attrs = data
        else:
            self.attrs = StrategyModel.model_validate(data)
        self.impact_strategy = self.get_impact_strategy()
        self.hazard_strategy = self.get_hazard_strategy()

    def get_measures(self) -> list[Union[ImpactMeasure, HazardMeasure]]:
        """Get the measures paths and types."""
        # Get measure paths using a database structure
        measure_paths = [
            db_path(object_dir=ObjectDir.measure, obj_name=measure) / f"{measure}.toml"
            for measure in self.attrs.measures
        ]
        return [MeasureFactory.get_measure_object(path) for path in measure_paths]

    def get_impact_strategy(self, validate=False) -> ImpactStrategy:
        measures = [
            measure
            for measure in self.get_measures()
            if isinstance(measure.attrs.type, ImpactType)
        ]
        return ImpactStrategy(
            measures=measures,
            validate=validate,
        )

    def get_hazard_strategy(self) -> HazardStrategy:
        measures = [
            measure
            for measure in self.get_measures()
            if isinstance(measure.attrs.type, HazardType)
        ]
        return HazardStrategy(measures=measures)
