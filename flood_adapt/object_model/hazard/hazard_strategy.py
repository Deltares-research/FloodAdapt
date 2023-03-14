from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure


class HazardStrategy:
    """Class containing only the hazard measures of a strategy"""

    def __init__(self, measures: list[HazardMeasure]) -> None:
        """
        Parameters
        ----------
        measures : list[HazardMeasure]
        """
        self.measures = measures
