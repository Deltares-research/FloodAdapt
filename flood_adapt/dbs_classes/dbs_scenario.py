import shutil
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.benefit import Benefit
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.scenario import Scenario


class DbsScenario(DbsTemplate):
    _type = "scenario"
    _folder_name = "scenarios"
    _object_model_class = Scenario

    def get(self, name: str) -> IScenario:
        """Returns a scenario object.

        Parameters
        ----------
        name : str
            name of the scenario to be returned

        Returns
        -------
        IScenario
            scenario object
        """
        return super().get(name).init_object_model()

    def list_objects(self) -> dict[str, Any]:
        """Returns a dictionary with info on the events that currently
        exist in the database.

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
        scenarios["finished"] = [
            obj.init_object_model().direct_impacts.has_run for obj in objects
        ]

        return scenarios

    def delete(self, name: str, toml_only: bool = False):
        """Deletes an already existing scenario in the database.

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
        results_path = self._database.output_path / "Scenarios" / name
        if results_path.exists():
            shutil.rmtree(results_path, ignore_errors=False)

    def edit(self, scenario: IScenario):
        """Edits an already existing scenario in the database.

        Parameters
        ----------
        scenario : IScenario
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
        output_path = self._database.output_path / "Scenarios" / scenario.attrs.name

        if output_path.exists():
            shutil.rmtree(output_path, ignore_errors=True)

    def _check_higher_level_usage(self, name: str):
        """Checks if a scenario is used in a benefit.

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
            Benefit.load_file(path)
            for path in self._database.benefits.list_objects()["path"]
        ]

        # Check in which benefits this scenario is used
        used_in_benefit = [
            benefit.attrs.name
            for benefit in benefits
            for scenario in benefit.check_scenarios()["scenario created"].to_list()
            if name == scenario
        ]

        return used_in_benefit
