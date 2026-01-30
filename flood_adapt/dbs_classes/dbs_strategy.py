from itertools import combinations

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.objects.measures.measures import MeasureType
from flood_adapt.objects.strategies.strategies import Strategy


class DbsStrategy(DbsTemplate[Strategy]):
    dir_name = "strategies"
    display_name = "Strategy"
    _object_class = Strategy
    _higher_lvl_object = "Scenario"

    def get(self, name: str) -> Strategy:
        strategy = super().get(name)
        measures = [
            self._database.measures.get(measure) for measure in strategy.measures
        ]
        strategy.initialize_measure_objects(measures)
        return strategy

    def add(self, obj: Strategy, overwrite: bool = False) -> None:
        self._assert_no_overlapping_measures(obj.measures)
        super().add(obj, overwrite)

    def _assert_no_overlapping_measures(self, measures: list[str]):
        """Validate if the combination of impact measures can happen, since impact measures cannot affect the same properties.

        Raises
        ------
        DatabaseError
            information on which combinations of measures have overlapping properties
        """
        measure_objects = [self._database.measures.get(measure) for measure in measures]
        impact_measures = [
            measure
            for measure in measure_objects
            if MeasureType.is_impact(measure.type)
        ]

        adapter = self._database.static.get_fiat_model()

        ids = [adapter.get_object_ids(measure) for measure in impact_measures]

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
                        impact_measures[comb[0][0]].name,
                        impact_measures[comb[1][0]].name,
                    )
                    counter += 1
            raise DatabaseError(msg)

    def used_by_higher_level(self, name: str) -> list[str]:
        """Check if a strategy is used in a scenario.

        Parameters
        ----------
        name : str
            name of the strategy to be checked

        Returns
        -------
        list[str]
            list of scenarios that use the strategy
        """
        scenarios = [
            self._database.scenarios.get(scn)
            for scn in self._database.scenarios.list_all()
        ]

        used_in_scenario = [
            scenario.name for scenario in scenarios if name == scenario.strategy
        ]

        return used_in_scenario
