from pathlib import Path
from typing import Any, List

import tomli

from flood_adapt.objects.events.event_set import EventSet
from flood_adapt.objects.events.events import (
    Event,
    Mode,
    Template,
)
from flood_adapt.objects.events.historical import HistoricalEvent
from flood_adapt.objects.events.hurricane import (
    HurricaneEvent,
    TranslationModel,
)
from flood_adapt.objects.events.synthetic import SyntheticEvent

__all__ = ["TranslationModel", "EventSet"]


class EventFactory:
    """Factory class for creating events.

    This class is used to create events based on a template.

    Attributes
    ----------
    _EVENT_TEMPLATES : dict[str, (Event, Event)]
        Dictionary mapping event templates to event classes and models
    """

    _EVENT_TEMPLATES = {
        Template.Hurricane: HurricaneEvent,
        Template.Historical: HistoricalEvent,
        Template.Synthetic: SyntheticEvent,
    }

    @staticmethod
    def get_event_from_template(template: Template) -> type[Event]:
        """Get the event class corresponding to the template.

        Parameters
        ----------
        template : str
            Name of the event template

        Returns
        -------
        Type[Event]
            Event template
        """
        if template not in EventFactory._EVENT_TEMPLATES:
            raise ValueError(f"Invalid event template: {template}")
        return EventFactory._EVENT_TEMPLATES[template]

    @staticmethod
    def read_template(filepath: Path) -> Template:
        """Get event template from toml file."""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if (template := toml.get("template")) is None:
            raise ValueError(f"Event template not found in {filepath}")

        return Template(template)

    @staticmethod
    def read_mode(filepath: Path) -> Mode:
        """Get event mode from toml file."""
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if toml.get("mode") is None:
            raise ValueError(f"Event mode not found in {filepath}")
        return Mode(toml.get("mode"))

    @staticmethod
    def load_file(toml_file: Path) -> Event:
        """Return event object based on toml file.

        Parameters
        ----------
        toml_file : str
            Template name

        Returns
        -------
        Event
            Event object
        """
        mode = EventFactory.read_mode(toml_file)
        if mode == Mode.risk:
            event_type = EventSet
        elif mode == Mode.single_event:
            template = Template(EventFactory.read_template(toml_file))
            event_type = EventFactory.get_event_from_template(template)
        else:
            raise ValueError(f"Invalid event mode: {mode}")
        return event_type.load_file(toml_file)

    @staticmethod
    def load_dict(attrs: dict[str, Any] | Event) -> Event | EventSet:
        """Return event object based on attrs dict.

        Parameters
        ----------
        attrs : dict[str, Any]
            Event attributes

        Returns
        -------
        Event
            Event object based on template
        """
        if isinstance(attrs, Event):
            mode = attrs.mode
            template = attrs.template
        else:
            mode = Mode(attrs.get("mode"))
            template = Template(attrs.get("template"))

        if mode == Mode.risk:
            # TODO Load events
            return EventSet(**attrs)
        elif mode == Mode.single_event:
            return EventFactory.get_event_from_template(template)(**attrs)
        else:
            raise ValueError(f"Invalid event mode: {mode}")

    @staticmethod
    def get_allowed_forcings(template) -> dict[str, List[str]]:
        return EventFactory.get_event_from_template(template).get_allowed_forcings()
