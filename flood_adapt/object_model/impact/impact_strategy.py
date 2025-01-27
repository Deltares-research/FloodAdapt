from flood_adapt.object_model.interface.measures import IMeasure


class ImpactStrategy:
    """Class containing only the impact measures of a strategy."""

    def __init__(self, measures: list[IMeasure]) -> None:
        """Set measures.

        Parameters
        ----------
        measures : list[IMeasure]
        """
        self.measures = measures
