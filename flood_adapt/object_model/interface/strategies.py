from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.measures import (
    Measure,
    MeasureType,
)
from flood_adapt.object_model.interface.object_model import IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    db_path,
)
from flood_adapt.object_model.measure_factory import (
    MeasureFactory,
)


class Strategy(IObjectModel):
    measures: list[str] = []

    def get_measures(self) -> list[Measure]:
        """Get the measures paths and types."""
        # Get measure paths using a database structure
        measure_paths = [
            db_path(object_dir=ObjectDir.measure, obj_name=measure) / f"{measure}.toml"
            for measure in self.measures
        ]
        return [MeasureFactory.get_measure_object(path) for path in measure_paths]

    def get_impact_strategy(self) -> ImpactStrategy:
        impact_measures = [
            measure
            for measure in self.get_measures()
            if MeasureType.is_impact(measure.type)
        ]
        return ImpactStrategy(
            measures=impact_measures,
        )

    def get_hazard_strategy(self) -> HazardStrategy:
        hazard_measures = [
            measure
            for measure in self.get_measures()
            if MeasureType.is_hazard(measure.type)
        ]
        return HazardStrategy(measures=hazard_measures)
