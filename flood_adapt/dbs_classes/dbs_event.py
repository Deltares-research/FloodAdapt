from pathlib import Path
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.eventset import EventSet
from flood_adapt.object_model.interface.events import Mode


class DbsEvent(DbsTemplate):
    _object_class = Event

    def get(self, name: str) -> Event:
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
        event_path = self.input_path / f"{name}" / f"{name}.toml"

        # Check if the object exists
        if not Path(event_path).is_file():
            raise ValueError(
                f"{self._object_class.class_name} '{name}' does not exist."
            )

        # Load event
        mode = Event.get_mode(event_path)
        if mode == Mode.single_event:
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            return EventFactory.get_event(template).load_file(event_path)
        elif mode == Mode.risk:
            return EventSet.load_file(event_path)

    def list_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the events that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        events = self._get_object_list()
        objects = [self.get(name) for name in events["name"]]
        events["description"] = [obj.attrs.description for obj in objects]
        events["objects"] = objects
        return events

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
        if self._database.site.attrs.standard_objects:
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
        scenarios = self._database.scenarios.list_objects()["objects"]

        # Check if event is used in a scenario
        used_in_scenario = [
            scenario.attrs.name
            for scenario in scenarios
            if name == scenario.attrs.event
        ]
        return used_in_scenario
