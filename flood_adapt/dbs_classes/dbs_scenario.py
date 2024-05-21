import os
import shutil
from typing import Any

from flood_adapt.dbs_classes.dbs_object import DbsObject
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.object_classes.scenario import Scenario


class DbsScenario(DbsObject):
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
        obj = super().get(name)
        obj._site_info = self._database.site
        obj._results_path = self._database.output_path.joinpath(
            self._folder_name, self.attrs.name
        )
        obj._direct_impacts = DirectImpacts(
            scenario=obj.attrs,
            database_input_path=self._database.database_input_path,
            results_path=obj.results_path,
        )

        return obj

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

    def check_higher_level_usage(self, name: str) -> list[str]:
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
