from flood_adapt.object_model.interface.database_user import IDatabaseUser
from flood_adapt.object_model.interface.measures import HazardMeasureModel


class HazardMeasure(IDatabaseUser):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model."""

    attrs: HazardMeasureModel
