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

    def get(self, name: str, load_all: bool = False) -> Event | EventSet:
        """Return an event object.

        Parameters
        ----------
        name : str
            name of the event to be returned

        Returns
        -------
        Event
            event object
        """
        # Get event path
        event_path = self.input_path / f"{name}" / f"{name}.toml"

        # Check if the object exists
        if not Path(event_path).is_file():
            raise DatabaseError(f"{self.display_name} '{name}' does not exist.")

        # Load event
        return EventFactory.load_file(event_path, load_all=load_all)

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
            self._database.scenarios.get(scn)
            for scn in self._database.scenarios.summarize_objects()["name"]
        ]

        # Check if event is used in a scenario
        used_in_scenario = [
            scenario.name for scenario in scenarios if name == scenario.event
        ]
        return used_in_scenario
