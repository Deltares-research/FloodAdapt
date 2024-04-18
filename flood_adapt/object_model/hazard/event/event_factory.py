from pathlib import Path
from typing import Any

import tomli

from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.event.hurricane import HurricaneEvent
from flood_adapt.object_model.hazard.event.synthetic import SyntheticEvent
from flood_adapt.object_model.interface.events import (
    EventMode,
    EventModel,
    EventTemplate,
    IEvent,
)


class EventFactory:
    """
    EventFactory class object for creating event objects from templates
    """

    @staticmethod
    def get_template(filepath: Path) -> EventTemplate:
        """Get event template from toml file"""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if toml.get("template") is None:
            raise ValueError(f"Event template not found in {filepath}")
        return toml.get("template")

    @staticmethod
    def get_mode(filepath: Path) -> EventMode:
        """Get event mode from toml file"""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        if toml.get("mode") is None:
            raise ValueError(f"Event mode not found in {filepath}")
        return toml.get("mode")

    @staticmethod
    def load_dict(attrs: dict[str, Any]) -> IEvent:
        """Returns event object based on attrs dict

        Parameters
        ----------
        attrs : dict[str, Any]
            Event attributes

        Returns
        -------
        IEvent
            Event object based on template
        """

        # Check template name and return object
        if isinstance(attrs, EventModel):
            template = attrs.template
        else:
            template = attrs.get("template")
        match template:
            case EventTemplate.Synthetic:
                return SyntheticEvent().load_dict(attrs)
            case EventTemplate.Hurricane | "Historical_hurricane":
                return HurricaneEvent().load_dict(attrs)
            case (
                EventTemplate.Historical
                | "Historical_offshore"
                | "Historical_nearshore"
            ):
                return HistoricalEvent().load_dict(attrs)
            case _:
                raise ValueError(f"Invalid event template: {template}")

    @staticmethod
    def load_file(toml_file: Path) -> IEvent:
        """Returns event object based on toml file

        Parameters
        ----------
        toml_file : str
            Template name

        Returns
        -------
        Event
            Event object
        """
        template = EventFactory.get_template(toml_file)

        match template:
            case EventTemplate.Synthetic:
                return SyntheticEvent.load_file(toml_file)
            case EventTemplate.Hurricane | "Historical_hurricane":
                return HurricaneEvent().load_file(toml_file)
            case (
                EventTemplate.Historical
                | "Historical_offshore"
                | "Historical_nearshore"
            ):
                return HistoricalEvent.load_file(toml_file)
            case _:
                raise ValueError(f"Invalid event template: {template}")
