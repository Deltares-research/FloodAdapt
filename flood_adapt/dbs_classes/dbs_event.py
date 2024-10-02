import shutil
from pathlib import Path
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.interface.events import IEvent


class DbsEvent(DbsTemplate):
    _type = "event"
    _folder_name = "events"
    _object_model_class = IEvent

    def get(self, name: str) -> IEvent:
        """Return an event object.

        Parameters
        ----------
        name : str
            name of the event to be returned

        Returns
        -------
        IEvent
            event object
        """
        # Get event path
        event_path = self._path / f"{name}" / f"{name}.toml"

        # Check if the object exists
        if not Path(event_path).is_file():
            raise ValueError(f"{self._type.capitalize()} '{name}' does not exist.")

        # Load event
        return EventFactory.load_file(event_path)

    def list_objects(self) -> dict[str, Any]:
        """Return a dictionary with info on the events that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        events = self._get_object_list()
        objects = [self._database.events.get(name) for name in events["name"]]
        events["description"] = [obj.attrs.description for obj in objects]
        events["objects"] = objects
        return events

    def copy(self, old_name: str, new_name: str, new_description: str):
        """Copy (duplicate) an existing object, and give it a new name.

        Parameters
        ----------
        old_name : str
            name of the existing measure
        new_name : str
            name of the new measure
        new_description : str
            description of the new measure
        """
        # Check if the provided old_name is valid
        if old_name not in self.list_objects()["name"]:
            raise ValueError(f"'{old_name}' {self._type} does not exist.")

        # First do a get and change the name and description
        copy_object = self.get(old_name)
        copy_object.attrs.name = new_name
        copy_object.attrs.description = new_description

        # After changing the name and description, receate the model to re-trigger the validators
        copy_object.attrs = type(copy_object.attrs)(**copy_object.attrs.dict())

        # Then a save. Checking whether the name is already in use is done in the save function
        self.save(copy_object)

        # Then save all the accompanied files
        src = self._path / old_name
        dest = self._path / new_name

        EXCLUDE = [".spw", ".toml"]
        for file in src.glob("*"):
            if file.suffix in EXCLUDE:
                continue
            shutil.copy(file, dest / file.name)

    def _check_standard_objects(self, name: str) -> bool:
        """Check if an event is a standard event.

        Parameters
        ----------
        name : str
            name of the event to be checked

        Returns
        -------
        bool
            True if the event is a standard event, False otherwise
        """
        # Check if event is a standard event
        if self._database.site.attrs.standard_objects.events:
            if name in self._database.site.attrs.standard_objects.events:
                return True

        return False

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Check if an event is used in a scenario.

        Parameters
        ----------
        name : str
            name of the event to be checked

        Returns
        -------
        list[str]
            list of scenarios that use the event
        """
        # Get all the scenarios
        scenarios = [
            self._database.scenarios.get(name)
            for name in self._database.scenarios.list_objects()["name"]
        ]

        # Check if event is used in a scenario
        used_in_scenario = [
            scenario.attrs.name
            for scenario in scenarios
            if name == scenario.attrs.event
        ]
        return used_in_scenario
