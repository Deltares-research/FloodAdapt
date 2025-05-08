from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.objects.projections.projections import Projection


class DbsProjection(DbsTemplate[Projection]):
    dir_name = "projections"
    display_name = "Projection"
    _object_class = Projection

    def _check_standard_objects(self, name: str) -> bool:
        """Check if a projection is a standard projection.

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
        if self._database.site.standard_objects:
            if self._database.site.standard_objects.projections:
                if name in self._database.site.standard_objects.projections:
                    return True

        return False

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Check if a projection is used in a scenario.

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
            self._database.scenarios.get(scn)
            for scn in self._database.scenarios.summarize_objects()["name"]
        ]

        # Check if projection is used in a scenario
        used_in_scenario = [
            scenario.name for scenario in scenarios if name == scenario.projection
        ]

        return used_in_scenario
