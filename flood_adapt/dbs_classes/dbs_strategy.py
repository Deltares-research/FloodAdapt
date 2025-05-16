from itertools import combinations

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.objects.measures.measures import MeasureType
from flood_adapt.objects.strategies.strategies import Strategy


class DbsStrategy(DbsTemplate[Strategy]):
    dir_name = "strategies"
    display_name = "Strategy"
    _object_class = Strategy

    def get(self, name: str) -> Strategy:
        strategy = super().get(name)
        measures = [
            self._database.measures.get(measure) for measure in strategy.measures
        ]
        strategy.initialize_measure_objects(measures)
        return strategy

    def save(
        self,
        object_model: Strategy,
        overwrite: bool = False,
    ):
        """Save an object in the database and all associated files.

        This saves the toml file and any additional files attached to the object.

        Parameters
        ----------
        object_model : Object
            object to be saved in the database
        overwrite : bool, optional
            whether to overwrite the object if it already exists in the
            database, by default False

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        object_exists = object_model.name in self.summarize_objects()["name"]

        # If you want to overwrite the object, and the object already exists, first delete it. If it exists and you
        # don't want to overwrite, raise an error.
        if overwrite and object_exists:
            self.delete(object_model.name, toml_only=True)
        elif not overwrite and object_exists:
            raise ValueError(
                f"'{object_model.name}' name is already used by another {self.display_name}. Choose a different name"
            )

        # Check if any measures overlap
        self._check_overlapping_measures(object_model.measures)

        # If the folder doesnt exist yet, make the folder and save the object
        if not (self.input_path / object_model.name).exists():
            (self.input_path / object_model.name).mkdir()

        # Save the object and any additional files
        object_model.save(
            self.input_path / object_model.name / f"{object_model.name}.toml",
        )

    def _check_overlapping_measures(self, measures: list[str]):
        """Validate if the combination of impact measures can happen, since impact measures cannot affect the same properties.

        Raises
        ------
        ValueError
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
            raise ValueError(msg)

    def _check_standard_objects(self, name: str) -> bool:
        """Check if a strategy is a standard strategy.

        Parameters
        ----------
        name : str
            name of the strategy to be checked

        Raises
        ------
        ValueError
            Raise error if strategy is a standard strategy.
        """
        # Check if strategy is a standard strategy
        if self._database.site.standard_objects:
            if self._database.site.standard_objects.strategies:
                if name in self._database.site.standard_objects.strategies:
                    return True
        return False

    def check_higher_level_usage(self, name: str) -> list[str]:
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
            for scn in self._database.scenarios.summarize_objects()["name"]
        ]

        used_in_scenario = [
            scenario.name for scenario in scenarios if name == scenario.strategy
        ]

        return used_in_scenario
