from flood_adapt.dbs_classes.dbs_object import DbsObject
from flood_adapt.object_model.object_classes.projection import Projection


class DbsProjection(DbsObject):
    _type = "projection"
    _folder_name = "projections"
    _object_model_class = Projection

    def _check_standard_objects(self, name: str) -> bool:
        """Checks if a projection is a standard projection.

        Parameters
        ----------
        name : str
            name of the projection to be checked

        Raises
        ------
        ValueError
            Raise error if projection is a standard projection.
        """
        # Check if projection is a standard projection
        if self._database.site.attrs.standard_objects.projections:
            if name in self._database.site.attrs.standard_objects.projections:
                return True

        return False

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Checks if a projection is used in a scenario.

        Parameters
        ----------
        name : str
            name of the projection to be checked

        Returns
        -------
        list[str]
            list of scenarios that use the projection
        """
        # Get all the scenarios
        scenarios = [
            self._database.scenarios.get(name=name)
            for name in self._database.scenarios.list_objects()["name"]
        ]

        # Check if projection is used in a scenario
        used_in_scenario = [
            scenario.attrs.name
            for scenario in scenarios
            if name == scenario.attrs.projection
        ]

        return used_in_scenario
