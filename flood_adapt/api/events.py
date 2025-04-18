# Event tab
import os
from pathlib import Path
from typing import Any, List, Optional, Type, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_classes.database import Database
from flood_adapt.object_model.hazard.event.event_factory import (
    EventFactory,
    HistoricalEvent,
    HurricaneEvent,
    SyntheticEvent,
    TranslationModel,
)
from flood_adapt.object_model.hazard.event.event_set import EventSet
from flood_adapt.object_model.hazard.forcing.discharge import DischargeConstant
from flood_adapt.object_model.hazard.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.forcing.plotting import (
    plot_forcing as _plot_forcing,
)
from flood_adapt.object_model.hazard.forcing.tide_gauge import TideGauge
from flood_adapt.object_model.hazard.forcing.waterlevels import SurgeModel, TideModel
from flood_adapt.object_model.hazard.interface.events import (
    Event,
    Mode,
    Template,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IDischarge,
    IForcing,
    IRainfall,
    IWaterlevel,
    IWind,
)
from flood_adapt.object_model.hazard.interface.models import TimeFrame
from flood_adapt.object_model.hazard.interface.timeseries import (
    CSVTimeseries,
    ShapeType,
    SyntheticTimeseries,
    TimeseriesFactory,
)
from flood_adapt.object_model.interface.config.sfincs import RiverModel
from flood_adapt.object_model.io import unit_system as us

# Ensure all objects are imported and available for use if this module is imported
__all__ = [
    "ShapeType",
    "Template",
    "TimeFrame",
    "ForcingType",
    "Mode",
    "EventFactory",
    "EventSet",
    "Event",
    "IForcing",
    "IDischarge",
    "IRainfall",
    "IWaterlevel",
    "IWind",
    "ForcingSource",
    "ForcingType",
    "Template",
    "TimeFrame",
    "IRainfall",
    "IWaterlevel",
    "IWind",
    "SyntheticEvent",
    "SyntheticEvent",
    "HistoricalEvent",
    "HistoricalEvent",
    "HurricaneEvent",
    "HurricaneEvent",
    "TranslationModel",
    "CSVTimeseries",
    "SyntheticTimeseries",
    "TimeseriesFactory",
    "DischargeConstant",
    "RiverModel",
    "SurgeModel",
    "TideModel",
    # functions
    "get_events",
    "get_event",
    "get_event_mode",
    "create_event",
    "create_event_set",
    "list_forcings",
    "get_allowed_forcings",
    "save_event",
    "save_timeseries_csv",
    "edit_event",
    "delete_event",
    "copy_event",
    "check_higher_level_usage",
    "download_wl_data",
    "read_csv",
    "plot_forcing",
    "save_cyclone_track",
    "get_cyclone_track_by_index",
]


def get_events() -> dict[str, Any]:
    """Get all events from the database.

    Returns
    -------
    dict[str, Any]
        A dictionary containing all events.
        Includes keys: 'name', 'description', 'path', 'last_modification_date', 'objects'
        Each value is a list of the corresponding attribute for each benefit.
    """
    return Database().events.list_objects()


def get_event(name: str) -> Event | EventSet:
    """Get an event from the database by name.

    Parameters
    ----------
    name : str
        The name of the event to retrieve.

    Returns
    -------
    Event | EventSet
        The event with the given name.

    Raises
    ------
    ValueError
        If the event with the given name does not exist.
    """
    return Database().events.get(name)


def get_event_mode(name: str) -> Mode:
    """Get the mode of an event from the database by name.

    Parameters
    ----------
    name : str

    Returns
    -------
    Mode
        The mode of the event with the given name, either `risk` or `single_event`.
    """
    filename = Database().events.input_path / f"{name}" / f"{name}.toml"
    return EventFactory.read_mode(filename)


def create_event(attrs: dict[str, Any] | Event) -> Event:
    """Create a event object from a dictionary of attributes.

    Parameters
    ----------
    attrs : Event [str, Any]
        Dictionary of attributes

    Returns
    -------
    Event
        Depending on attrs.template an event object.
        Can be of type: Synthetic, Historical, Hurricane.
    """
    return EventFactory.load_dict(attrs)


def create_event_set(
    attrs: dict[str, Any] | EventSet, sub_events: list[Event]
) -> EventSet:
    """Create a event set object from a dictionary of attributes.

    Parameters
    ----------
    attrs : EventSet [str, Any]
        Dictionary of attributes
    sub_events : list[Event]
        List of events in the event set

    Returns
    -------
    EventSet
        EventSet object
    """
    return EventSet(**attrs, sub_events=sub_events)


def list_forcings() -> list[Type[IForcing]]:
    return ForcingFactory.list_forcings()


def get_allowed_forcings(template: Template) -> dict[str, List[str]]:
    return EventFactory.get_allowed_forcings(template)


def save_event(event: Event) -> None:
    """Save an event object to the database.

    Parameters
    ----------
    event : Event
        The event object to save.

    Raises
    ------
    ValueError
        If the event object is not valid.
    """
    Database().events.save(event)


def save_timeseries_csv(name: str, event: Event, df: pd.DataFrame) -> None:
    """Save timeseries data to a csv file.

    Parameters
    ----------
    name : str
        Name of the event
    event : Event
        Event object
    df : pd.DataFrame
        Dataframe of timeseries data
    """
    Database().write_to_csv(name, event, df)


def edit_event(event: Event) -> None:
    """Edit an event object in the database.

    Parameters
    ----------
    event : Event
        The event object to edit.

    Raises
    ------
    ValueError
        If the event object does not exist.
        If the event is used in a scenario.
    """
    Database().events.edit(event)


def delete_event(name: str) -> None:
    """Delete an event from the database.

    Parameters
    ----------
    name : str
        The name of the event to delete.

    Raises
    ------
    ValueError
        If the event does not exist.
        If the event is used in a scenario.
    """
    Database().events.delete(name)


def copy_event(old_name: str, new_name: str, new_description: str) -> None:
    """Copy an event in the database.

    Parameters
    ----------
    old_name : str
        The name of the event to copy.
    new_name : str
        The name of the new event.
    new_description : str
        The description of the new event
    """
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
    tide_gauge: TideGauge, time: TimeFrame, units: us.UnitTypesLength, out_path: str
) -> pd.DataFrame:
    """Download water level data from a station or tide gauge.

    Parameters
    ----------
    tide_gauge : TideGauge
        Tide gauge object to download data from
    time: TimeFrame
        Time model object containing start and end time
    units : UnitTypesLength
        Units that data the returned data will be converted to
    out_path : str
        Path to save the data to
    """
    return tide_gauge.get_waterlevels_in_time_frame(
        time=time,
        units=units,
        out_path=Path(out_path),
    )


def read_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    """Read a csv file into a pandas DataFrame.

    Parameters
    ----------
    csvpath : Union[str, os.PathLike]
        Path to the csv file

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the csv file
    """
    return read_csv(csvpath)


def plot_forcing(
    event: Event, forcing_type: ForcingType
) -> tuple[str, Optional[List[Exception]]]:
    """Plot forcing data for an event.

    Parameters
    ----------
    event : Event
        The event object
    forcing_type : ForcingType
        The type of forcing data to plot
    """
    return _plot_forcing(event, Database().site, forcing_type)


def save_cyclone_track(event: Event, track: TropicalCyclone):
    """Save cyclone track data to the event folder.

    Parameters
    ----------
    event : Event
        The event object
    track : TropicalCyclone
        The cyclone track data
    """
    Database().write_cyc(event, track)


def get_cyclone_track_by_index(index: int) -> TropicalCyclone:
    return Database().static.get_cyclone_track_database().get_track(index)
