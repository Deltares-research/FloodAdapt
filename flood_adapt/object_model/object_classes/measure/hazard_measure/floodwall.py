from flood_adapt.object_model.models.measures import (
    FloodWallModel,
)
from flood_adapt.object_model.object_classes.measure.hazard_measure.hazard_measure import (
    HazardMeasure,
)


class FloodWall(HazardMeasure):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height"""

    _attrs = FloodWallModel
