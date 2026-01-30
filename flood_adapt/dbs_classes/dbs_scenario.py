from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.benefit_runner import BenefitRunner


class DbsScenario(DbsTemplate[Scenario]):
    dir_name = "scenarios"
    display_name = "Scenario"
    _object_class = Scenario
    _higher_lvl_object = "Benefit"

    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the events that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        scenarios = super().summarize_objects()

        scenarios["Projection"] = [obj.projection for obj in self._objects.values()]
        scenarios["Event"] = [obj.event for obj in self._objects.values()]
        scenarios["Strategy"] = [obj.strategy for obj in self._objects.values()]
        scenarios["finished"] = [self.has_run_check(scn) for scn in self._objects]

        return scenarios

    def used_by_higher_level(self, name: str) -> list[str]:
        """Check if a scenario is used in a benefit.

        Parameters
        ----------
        name : str
            name of the scenario to be checked

        Returns
        -------
            list[str]
                list of benefits that use the scenario
        """
        benefits = self._database.benefits.list_all()
        used_in_benefit = []
        for benefit in benefits:
            runner = BenefitRunner(database=self._database, benefit=benefit)
            scenarios = runner.scenarios["scenario created"].to_list()
            for scenario in scenarios:
                if name == scenario:
                    used_in_benefit.append(benefit.name)

        return used_in_benefit

    def equal_hazard_components(self, left: Scenario, right: Scenario) -> bool:
        """Check if two scenarios have the same hazard components.

        Parameters
        ----------
        left : Scenario
            first scenario to be compared
        right : Scenario
            second scenario to be compared

        Returns
        -------
            bool
                True if the scenarios have the same hazard components, False otherwise
        """
        event_left = self._database.events.get(left.event)
        event_right = self._database.events.get(right.event)
        equal_events = event_left == event_right

        left_projection = self._database.projections.get(left.projection)
        right_projection = self._database.projections.get(right.projection)
        equal_projection = (
            left_projection.physical_projection == right_projection.physical_projection
        )

        left_strategy = self._database.strategies.get(
            left.strategy
        ).get_hazard_strategy()
        right_strategy = self._database.strategies.get(
            right.strategy
        ).get_hazard_strategy()
        equal_strategy = left_strategy == right_strategy

        return equal_events and equal_projection and equal_strategy

    def has_run_check(self, name: str) -> bool:
        """Check if the scenario has been run.

        Parameters
        ----------
        name : str
            name of the scenario to be checked

        Returns
        -------
            bool
                True if the scenario has been run, False otherwise
        """
        results_path = self.output_path / name
        return finished_file_exists(results_path)
