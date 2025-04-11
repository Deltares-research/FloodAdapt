from flood_adapt.objects.measures.measures import Measure


class HazardStrategy:
    """Class containing only the hazard measures of a strategy.

    Parameters
    ----------
    measures : list[Measure]
    """

    def __init__(self, measures: list[Measure]) -> None:
        self.measures = measures

    def __eq__(self, other):
        if not isinstance(other, HazardStrategy):
            # don't attempt to compare against unrelated types
            return NotImplemented
        names_1 = [measure.name for measure in self.measures]
        names_2 = [measure.name for measure in other.measures]

        return set(names_1) == set(names_2)
