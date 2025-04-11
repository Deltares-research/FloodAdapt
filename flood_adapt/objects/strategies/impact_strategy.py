from flood_adapt.objects.measures.measures import Measure


class ImpactStrategy:
    """Class containing only the impact measures of a strategy."""

    def __init__(self, measures: list[Measure]) -> None:
        """Set measures.

        Parameters
        ----------
        measures : list[Measure]
        """
        self.measures = measures
