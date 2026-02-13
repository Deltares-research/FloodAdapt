from pathlib import Path

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.objects.events.event_factory import EventFactory
from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import Event


class DbsEvent(DbsTemplate[Event]):
    dir_name = "events"
    display_name = "Event"
    _object_class = Event
    _higher_lvl_object = "Scenario"

    def _read_object(self, path: Path) -> Event:
        return EventFactory.load_file(path)

    def get_event_set(self, name: str) -> EventSet:
        """Get the event set that the event belongs to."""
        event_set = self.get(name)
        if not isinstance(event_set, EventSet):
            raise DatabaseError(f"Event {name} is not an event set.")
        path = self._object_path(self.input_path, event_set.name)
        event_set.load_sub_events(file_path=path)
        return event_set

    def used_by_higher_level(self, name: str) -> list[str]:
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
        scenarios = self._database.scenarios.list_all()

        # Check if event is used in a scenario
        used_in_scenario = [
            scenario.name for scenario in scenarios if name == scenario.event
        ]
        return used_in_scenario
