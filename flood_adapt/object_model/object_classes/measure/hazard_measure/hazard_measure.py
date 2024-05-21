from flood_adapt.object_model.models.measures import HazardMeasureModel
from flood_adapt.object_model.object_classes.measure.measure import Measure


class HazardMeasure(Measure):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model"""

    _attrs = HazardMeasureModel
