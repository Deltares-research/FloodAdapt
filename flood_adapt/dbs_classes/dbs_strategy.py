from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.strategy import Strategy


class DbsStrategy(DbsTemplate):
    _type = "strategy"
    _folder_name = "strategies"
    _object_model_class = Strategy

    def _check_standard_objects(self, name: str):
        """Checks if a strategy is a standard strategy.

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
        if self._database.site.attrs.standard_objects.strategies:
            if name in self._database.site.attrs.standard_objects.strategies:
                raise ValueError(
                    f"'{name}' strategy cannot be deleted since it is a standard strategy."
                )

    def _check_higher_level_usage(self, name: str):
        """Checks if a strategy is used in a scenario.

        Parameters
        ----------
        name : str
            name of the strategy to be checked

        Returns
        -------
        list[str]
            list of scenarios that use the strategy
        """
        # Get all the scenarios
        scenarios = [
            Scenario.load_file(path)
            for path in self._database.scenarios.list_objects()["path"]
        ]

        # Check if strategy is used in a scenario
        used_in_scenario = [
            scenario.attrs.name
            for scenario in scenarios
            if name == scenario.attrs.strategy
        ]

        return used_in_scenario
