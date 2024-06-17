from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure


class HazardStrategy:
    """Class containing only the hazard measures of a strategy.

    Parameters
    ----------
    measures : list[HazardMeasure]
    """

    def __init__(self, measures: list[HazardMeasure]) -> None:
        self.measures = measures

    def __eq__(self, other):
        if not isinstance(other, HazardStrategy):
            # don't attempt to compare against unrelated types
            return NotImplemented
        names_1 = [measure.attrs.name for measure in self.measures]
        names_2 = [measure.attrs.name for measure in other.measures]

        return set(names_1) == set(names_2)
