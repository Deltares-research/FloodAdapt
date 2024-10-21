from flood_adapt.object_model.interface.measures import HazardMeasureModel, IMeasure


class HazardMeasure(IMeasure[HazardMeasureModel]):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model."""

    attrs: HazardMeasureModel
