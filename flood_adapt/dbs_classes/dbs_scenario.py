import shutil
from typing import Any

from flood_adapt.dbs_classes.dbs_event import DbsEvent
from flood_adapt.dbs_classes.dbs_projection import DbsProjection
from flood_adapt.dbs_classes.dbs_strategy import DbsStrategy
from flood_adapt.dbs_classes.dbs_template import DbsTemplate, ObjectModel
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

    def set_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """Locks the element in the database to prevent other processes from accessing it. The object can be locked by
        providing either the model_object or the name. If both are provided, the model_object is used. An element can
        be locked multiple times. For example, if 2 scenario's are running that use the same event, it should be locked
        twice. The lock is only released when both scenario's are finished. When locking a scenario, also lock the strategy,
        projection and event it consists of.

        Parameters
        ----------
        model_object : ObjectModel, optional
            The model_object to lock, by default None
        name : str, optional
            The name of the model_object to lock, by default None

        Raises
        ------
        ValueError
            Raise error if both model_object and name are None.
        """
        super().set_lock(model_object, name)
        DbsStrategy.set_lock(self, name = model_object.attrs.strategy)
        DbsProjection.set_lock(self, name = model_object.attrs.projection)
        DbsEvent.set_lock(self, name = model_object.attrs.event)

    def release_lock(self, model_object: ObjectModel = None, name: str = None) -> None:
        """Releases the lock on the element in the database. The object can be unlocked by providing either the
        model_object or the name. If both are provided, the model_object is used. An element can be locked multiple
        times. For example, if 2 scenario's are running that use the same event, it should be locked twice. The lock
        is only released when both scenario's are finished. When unlocking a scenario, also unlock the strategy,
        projection and event it consists of.

        Parameters
        ----------
        model_object : ObjectModel, optional
            The model_object to unlock, by default None
        name : str, optional
            The name of the model_object to unlock, by default None

        Raises
        ------
        ValueError
            Raise error if both model_object and name are None.
        """
        super().release_lock(model_object, name)
        DbsStrategy.release_lock(self, name = model_object.attrs.strategy)
        DbsProjection.release_lock(self, name = model_object.attrs.projection)
        DbsEvent.release_lock(self, name = model_object.attrs.event)
        

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

    def delete(self, name: str):
        """Deletes an already existing scenario and the results in the database.

        Parameters
        ----------
        name : str
            name of the scenario to be deleted
        """

        # First delete the scenario
        super().delete(name)

        # Then delete the results
        if self._check_higher_level_usage(name):
            results_path = (
                self._database.input_path.parent / "output" / "Scenarios" / name
            )
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
        try:
            super().edit(scenario)
        except ValueError as e:
            # If not, raise error
            raise ValueError(e)
        else:
            # Delete output if edited
            output_path = (
                self._database.input_path.parent
                / "output"
                / "Scenarios"
                / scenario.attrs.name
            )

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
            for scenario in benefit.check_scenarios()[
                "scenario created"
            ].to_list()
            if name == scenario
        ]

        return used_in_benefit
