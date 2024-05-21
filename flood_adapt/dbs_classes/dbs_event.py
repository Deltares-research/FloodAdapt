import os
from typing import Any

from flood_adapt.dbs_classes.dbs_object import DbsObject
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.object_classes.event.event import Event
from flood_adapt.object_model.object_classes.event.event_factory import EventFactory


class DbsEvent(DbsObject):
    _type = "event"
    _folder_name = "events"
    _object_model_class = Event

    def get(self, name: str) -> IEvent:
        """Returns an event object.

        Parameters
        ----------
        name : str
            name of the event to be returned

        Returns
        -------
        IEvent
            event object
        """
        # Load event
        # event_template = Event.get_template(event_path)
        # event = EventFactory.get_event(event_template).load_file(event_path)
        event_obj = super().get(name)
        event_obj = EventFactory.get_event(event_obj)
        return event_obj.load_additional_data(self._path)        

    def list_objects(self) -> dict[str, Any]:
        """Returns a dictionary with info on the events that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        events = self._get_object_list()
        objects = [Hazard.get_event_object(path) for path in events["path"]]
        events["name"] = [obj.attrs.name for obj in objects]
        events["description"] = [obj.attrs.description for obj in objects]
        events["objects"] = objects
        return events

    def _check_standard_objects(self, name: str) -> bool:
        """Checks if an event is a standard event.

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
        """Checks if an event is used in a scenario.

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
            self._database.scenarios.get(os.path.basename(path))
            for path in self._database.scenarios.list_objects()["path"]
        ]

        # Check if event is used in a scenario
        used_in_scenario = [
            scenario.attrs.name
            for scenario in scenarios
            if name == scenario.attrs.event
        ]
        return used_in_scenario
