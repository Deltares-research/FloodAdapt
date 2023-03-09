from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure


class HazardStrategy:
    """Subclass of Strategy describing a strategy with only hazard measures"""

    def __init__(self, measures: list[HazardMeasure]) -> None:
        self.measures = measures
