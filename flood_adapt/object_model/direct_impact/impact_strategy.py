from itertools import combinations

from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure


class ImpactStrategy:
    """Class containing only the impact measures of a strategy"""

    def __init__(self, measures: list[ImpactMeasure], validate=False) -> None:
        """Sets measures and validates the combination

        Parameters
        ----------
        measures : list[ImpactMeasure]
        """
        self.measures = measures
        if validate:
            self.validate()

    def validate(self):
        """Validates if the combination of impact measures can happen,
        since impact measures cannot affect the same properties.

        Raises
        ------
        ValueError
            information on which combinations of measures have overlapping properties
        """
        # Get ids of objects affected for each measure
        ids = [measure.get_object_ids() for measure in self.measures]

        # Get all possible pairs of measures and check overlapping buildings for each measure
        combs = list(combinations(enumerate(ids), 2))
        common_elements = []
        for comb in combs:
            common_elements.append(list(set(comb[0][1]).intersection(comb[1][1])))

        # If there is any combination with overlapping buildings raise Error and do not allow for Strategy object creation
        overlapping = [len(k) > 0 for k in common_elements]
        if any(overlapping):
            msg = "Cannot create strategy! There are overlapping buildings for which measures are proposed"
            counter = 0
            for i, comb in enumerate(combs):
                if overlapping[i]:
                    if counter > 0:
                        msg += " and"
                    msg += " between '{}' and '{}'".format(
                        self.measures[comb[0][0]].attrs.long_name,
                        self.measures[comb[1][0]].attrs.long_name,
                    )
                    counter += 1
            raise ValueError(msg)
