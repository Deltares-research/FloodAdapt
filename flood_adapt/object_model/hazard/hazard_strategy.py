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
            return False

        names_1 = sorted([measure.attrs.name for measure in self.measures])
        names_2 = sorted([measure.attrs.name for measure in other.measures])

        return names_1 == names_2
