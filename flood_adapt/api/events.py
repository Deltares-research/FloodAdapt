# Event tab
import os
from pathlib import Path
from typing import Any, List, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.hazard.event.event_factory import (
    EventFactory,
    HistoricalEvent,
    HistoricalEventModel,
    HurricaneEvent,
    HurricaneEventModel,
    SyntheticEvent,
    SyntheticEventModel,
    TranslationModel,
)
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.event.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.interface.forcing import (
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import (
    TIDAL_PERIOD,
    ForcingSource,
    ForcingType,
    Mode,
    ShapeType,
    Template,
    TimeModel,
)
from flood_adapt.object_model.interface.events import IEvent, IEventModel

# Ensure all objects are imported and available for use if this module is imported
__all__ = [
    "ShapeType",
    "Template",
    "TimeModel",
    "ForcingType",
    "Mode",
    "EventFactory",
    "IEvent",
    "IForcing",
    "IDischarge",
    "IRainfall",
    "IWaterlevel",
    "IWind",
    "TIDAL_PERIOD",
    "ForcingSource",
    "ForcingType",
    "Template",
    "TimeModel",
    "IDischarge",
    "IRainfall",
    "IWaterlevel",
    "IWind",
    "SyntheticEvent",
    "SyntheticEventModel",
    "HistoricalEventModel",
    "HistoricalEvent",
    "HurricaneEvent",
    "HurricaneEventModel",
    "TranslationModel",
]


def get_events() -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return Database().events.list_objects()


def get_event(name: str) -> IEvent | EventSet:
    return Database().events.get(name)


def get_event_mode(name: str) -> str:
    filename = Database().events.input_path / f"{name}" / f"{name}.toml"
    return EventFactory.read_mode(filename)


def create_event(attrs: dict[str, Any] | IEventModel) -> IEvent | EventSet:
    """Create a event object from a dictionary of attributes.

    Parameters
    ----------
    attrs : IEventModel [str, Any]
        Dictionary of attributes

    Returns
    -------
    Event
        Depending on attrs.template an event object.
        Can be of type: Synthetic, Historical_nearshore, Historical_offshore, or Historical_hurricane.
    """
    return EventFactory.load_dict(attrs)


def list_forcing_types() -> list[str]:
    return ForcingFactory.list_forcing_types()


def list_forcings(as_string: bool) -> list[str] | list[IForcing]:
    return ForcingFactory.list_forcings(as_string=as_string)


def get_allowed_forcings(template: Template) -> dict[str, List[str]]:
    return EventFactory.get_allowed_forcings(template)


def get_template_description(template: Template) -> str:
    return EventFactory.get_template_description(template)


def save_event(event: IEvent) -> None:
    Database().events.save(event)


def save_timeseries_csv(name: str, event: IEvent, df: pd.DataFrame) -> None:
    Database().write_to_csv(name, event, df)


def edit_event(event: IEvent) -> None:
    Database().events.edit(event)


def delete_event(name: str) -> None:
    Database().events.delete(name)


def copy_event(old_name: str, new_name: str, new_description: str) -> None:
    Database().events.copy(old_name, new_name, new_description)


def check_higher_level_usage(name: str) -> list[str]:
    """Check if an event is used in a scenario.

    Parameters
    ----------
    name : str
        name of the event to be checked

    Returns
    -------
    list[str]
        list of scenario names where the event is used

    """
    return Database().events.check_higher_level_usage(name)


def download_wl_data(
    tide_gauge: TideGauge, time: TimeModel, units: uv.UnitTypesLength, out_path: str
) -> pd.DataFrame:
    return tide_gauge.get_waterlevels_in_time_frame(
        time=time,
        units=units,
        out_path=Path(out_path),
    )


def read_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    return read_csv(csvpath)


def plot_forcing(event: IEvent, forcingtype: ForcingType, **kwargs) -> str | None:
    return event.plot_forcing(forcingtype, **kwargs)


def save_cyclone_track(event: IEvent, track: TropicalCyclone):
    Database().write_cyc(event, track)


def get_cyclone_track_by_index(index: int) -> TropicalCyclone:
    return Database().cyclone_track_database.get_track(index)
