import shutil
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.scenario import Scenario


class DbsScenario(DbsTemplate[Scenario]):
    _object_class = Scenario

    def list_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the events that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        scenarios = super().list_objects()
        objects = scenarios["objects"]
        scenarios["Projection"] = [obj.attrs.projection for obj in objects]
        scenarios["Event"] = [obj.attrs.event for obj in objects]
        scenarios["Strategy"] = [obj.attrs.strategy for obj in objects]
        scenarios["finished"] = [obj.has_run_check() for obj in objects]

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

    def edit(self, object_model: Scenario):
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
        super().edit(object_model)

        # Delete output if edited
        output_path = self.output_path / object_model.attrs.name
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
        # Get all the benefits
        benefits = [
            self._database.benefits.get(name)
            for name in self._database.benefits.list_objects()["name"]
        ]

        # Check in which benefits this scenario is used
        used_in_benefit = [
            benefit.attrs.name
            for benefit in benefits
            for scenario in benefit.check_scenarios()["scenario created"].to_list()
            if name == scenario
        ]

        return used_in_benefit
