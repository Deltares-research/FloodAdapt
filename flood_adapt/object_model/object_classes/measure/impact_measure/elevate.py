from flood_adapt.object_model.models.measures import ElevateModel
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)


class Elevate(ImpactMeasure):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height"""

    _attrs = ElevateModel