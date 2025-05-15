import shutil
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.utils import finished_file_exists
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.benefit_runner import BenefitRunner


class DbsScenario(DbsTemplate[Scenario]):
    dir_name = "scenarios"
    display_name = "Scenario"
    _object_class = Scenario

    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the events that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        scenarios = super().summarize_objects()
        scenarios["Projection"] = [
            self._read_variable_in_toml("projection", path)
            for path in scenarios["path"]
        ]
        scenarios["Event"] = [
            self._read_variable_in_toml("event", path) for path in scenarios["path"]
        ]
        scenarios["Strategy"] = [
            self._read_variable_in_toml("strategy", path) for path in scenarios["path"]
        ]
        scenarios["finished"] = [self.has_run_check(scn) for scn in scenarios["name"]]

        return scenarios

    def delete(self, name: str, toml_only: bool = False):
        """Delete an already existing scenario in the database.

        Parameters
        ----------
        name : str
            name of the scenario to be deleted
        toml_only : bool, optional
            whether to only delete the toml file or the entire folder. If the folder is empty after deleting the toml,
            it will always be deleted. By default False

        Raises
        ------
        ValueError
            Raise error if scenario to be deleted is already in use.
        """
        # First delete the scenario
        super().delete(name, toml_only)

        # Then delete the results
        if (self.output_path / name).exists():
            shutil.rmtree(self.output_path / name, ignore_errors=False)

    def edit(self, scenario: Scenario):
        """Edits an already existing scenario in the database.

        Parameters
        ----------
        scenario : Scenario
            scenario to be edited in the database

        Raises
        ------
        ValueError
            Raise error if name is already in use.
        """
        # Check if it is possible to edit the scenario. This then also covers checking whether the
        # scenario is already used in a higher level object. If this is the case, it cannot be edited.
        super().edit(scenario)

        # Delete output if edited
        output_path = self.output_path / scenario.name
        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

    def check_higher_level_usage(self, name: str) -> list[str]:
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
        benefits = [
            self._database.benefits.get(benefit)
            for benefit in self._database.benefits.summarize_objects()["name"]
        ]
        used_in_benefit = []
        for benefit in benefits:
            runner = BenefitRunner(database=self._database, benefit=benefit)
            scenarios = runner.check_scenarios()["scenario created"].to_list()
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
