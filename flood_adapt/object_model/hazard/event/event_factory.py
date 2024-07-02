from pathlib import Path
from typing import Any, Tuple

import tomli

from flood_adapt.object_model.hazard.event.historical import (
    HistoricalEvent,
    HistoricalEventModel,
)
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
    HurricaneEventModel,
)
from flood_adapt.object_model.hazard.event.synthetic import (
    SyntheticEvent,
    SyntheticEventModel,
)
from flood_adapt.object_model.hazard.interface.events import (
    IEvent,
    IEventFactory,
    IEventModel,
    Mode,
    Template,
)


class EventFactory(IEventFactory):
    """Factory class for creating events.

    This class is used to create events based on a template.

    Attributes
    ----------
    _EVENT_TEMPLATES : dict[str, (IEvent, IEventModel)]
        Dictionary mapping event templates to event classes and models
    """

    _EVENT_TEMPLATES = {
        Template.Hurricane: (HurricaneEvent, HurricaneEventModel),
        Template.Historical_nearshore: (HistoricalEvent, HistoricalEventModel),
        Template.Historical_offshore: (HistoricalEvent, HistoricalEventModel),
        Template.Synthetic: (SyntheticEvent, SyntheticEventModel),
        # TODO remove below, and add to db update script
        "Historical_offshore": (HistoricalEvent, HistoricalEventModel),
        "Historical_nearshore": (HistoricalEvent, HistoricalEventModel),
    }

    @staticmethod
    def get_event_and_class(template: Template) -> Tuple[IEvent, IEventModel]:
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
    def get_template(filepath: Path) -> Template:
        """Get event template from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if toml.get("template") is None:
            raise ValueError(f"Event template not found in {filepath}")
        return toml.get("template")

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """Get event mode from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if toml.get("mode") is None:
            raise ValueError(f"Event mode not found in {filepath}")
        return toml.get("mode")

    @staticmethod
    def load_file(toml_file: Path) -> IEvent:
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
        template = Template(EventFactory.get_template(toml_file))
        event_type, _ = EventFactory.get_event_and_class(template)
        return event_type.load_file(toml_file)

    @staticmethod
    def load_dict(attrs: dict[str, Any]) -> IEvent:
        """Return event object based on attrs dict.

        Parameters
        ----------
        attrs : dict[str, Any]
            Event attributes

        Returns
        -------
        IEvent
            Event object based on template
        """
        if issubclass(attrs, IEventModel):
            template = attrs.template
        else:
            template = attrs.get("template")

        return EventFactory.get_event_class(template).load_dict(attrs)
