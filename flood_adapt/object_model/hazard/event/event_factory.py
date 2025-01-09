from pathlib import Path
from typing import Any, List, Type

import tomli

from flood_adapt.object_model.hazard.event.event_set import (
    EventSet,
)
from flood_adapt.object_model.hazard.event.historical import (
    HistoricalEvent,
    HistoricalEventModel,
)
from flood_adapt.object_model.hazard.event.hurricane import (
    HurricaneEvent,
    HurricaneEventModel,
    TranslationModel,
)
from flood_adapt.object_model.hazard.event.synthetic import (
    SyntheticEvent,
    SyntheticEventModel,
)
from flood_adapt.object_model.hazard.interface.events import (
    IEvent,
    IEventModel,
    Mode,
    Template,
)

__all__ = ["TranslationModel"]


class EventFactory:
    """Factory class for creating events.

    This class is used to create events based on a template.

    Attributes
    ----------
    _EVENT_TEMPLATES : dict[str, (Event, IEventModel)]
        Dictionary mapping event templates to event classes and models
    """

    _EVENT_TEMPLATES = {
        Template.Hurricane: (HurricaneEvent, HurricaneEventModel),
        Template.Historical: (HistoricalEvent, HistoricalEventModel),
        Template.Synthetic: (SyntheticEvent, SyntheticEventModel),
    }

    @staticmethod
    def get_event_from_template(template: Template) -> Type[IEvent]:
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
        return EventFactory._EVENT_TEMPLATES[template][0]

    @staticmethod
    def get_eventmodel_from_template(template: Template) -> type[IEventModel]:
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
        return EventFactory._EVENT_TEMPLATES[template][1]

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
    def load_file(toml_file: Path) -> IEvent | EventSet:
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
    def load_dict(attrs: dict[str, Any] | IEventModel) -> IEvent | EventSet:
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
        if isinstance(attrs, IEventModel):
            mode = attrs.mode
            template = attrs.template
        else:
            mode = Mode(attrs.get("mode"))
            template = Template(attrs.get("template"))

        if mode == Mode.risk:
            return EventSet.load_dict(attrs)
        elif mode == Mode.single_event:
            return EventFactory.get_event_from_template(template).load_dict(attrs)
        else:
            raise ValueError(f"Invalid event mode: {mode}")

    @staticmethod
    def get_allowed_forcings(template) -> dict[str, List[str]]:
        return EventFactory.get_event_from_template(
            template
        )._attrs_type.get_allowed_forcings()

    @staticmethod
    def get_default_eventmodel(template: Template) -> IEventModel:
        match template:
            case Template.Synthetic:
                return SyntheticEventModel.default()
            case Template.Historical:
                return HistoricalEventModel.default()
            case Template.Hurricane:
                return HurricaneEventModel.default()
            case _:
                raise ValueError(f"Invalid event template: {template}")
