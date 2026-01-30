from pathlib import Path

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.objects.events.event_factory import EventFactory
from flood_adapt.objects.events.events import Event


class DbsEvent(DbsTemplate[Event]):
    dir_name = "events"
    display_name = "Event"
    _object_class = Event
    _higher_lvl_object = "Scenario"

    def _read_object(self, path: Path) -> Event:
        return EventFactory.load_file(path)

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
