# Event tab
import inspect
import os
import types
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_controller import IDatabase
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.interface.events import (
    IEvent,
    IHistoricalHurricane,
    IHistoricalNearshore,
    IHistoricalOffshore,
    ISynthetic,
)
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength


def get_events(database: IDatabase) -> dict[str, Any]:
    """Returns a dictionary with info on the events that currently
    exist in the database

    Parameters
    ----------
    database : IDatabase
        Database object

    Returns
    -------
    dict[str, Any]
        Dictionary with info on the events
    """
    return database.events.list_objects()


def get_event(name: str, database: IDatabase) -> IEvent:
    """Returns the event object with the specified name from the database

    Parameters
    ----------
    name : str
        name of the object to be returned
    database : IDatabase
        database object

    Returns
    -------
    IEvent
        The event object with the specified name
    """
    return database.events.get(name)


def get_event_mode(name: str, database: IDatabase) -> str:
    filename = database.input_path / "events" / f"{name}" / f"{name}.toml"
    return Event.get_mode(filename)


def create_synthetic_event(attrs: dict[str, Any]) -> ISynthetic:
    """Create a synthetic event object from a dictionary of attributes

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes

    Returns
    -------
    Synthetic
        Synthetic event object
    """
    return EventFactory.get_event("Synthetic").load_dict(attrs)


def create_historical_nearshore_event(attrs: dict[str, Any]) -> IHistoricalNearshore:
    """Create a historical nearshore event object from a dictionary of attributes

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes

    Returns
    -------
    HistoricalNearshore
        Historical nearshore event object
    """
    return EventFactory.get_event("Historical_nearshore").load_dict(attrs)


def create_historical_offshore_event(attrs: dict[str, Any]) -> IHistoricalOffshore:
    """Create a historical offshore event object from a dictionary of attributes

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes

    Returns
    -------
    HistoricalNearshore
        Historical offshore event object
    """
    return EventFactory.get_event("Historical_offshore").load_dict(attrs)


def create_historical_hurricane_event(attrs: dict[str, Any]) -> IHistoricalHurricane:
    """Create a historical hurricane event object from a dictionary of attributes

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes

    Returns
    -------
    HistoricalHurricane
        Historical hurricane event object
    """
    return EventFactory.get_event("Historical_hurricane").load_dict(attrs)


def save_event_toml(event: IEvent, database: IDatabase) -> None:
    """Save the event to the database as a .toml file

    Parameters
    ----------
    event : IEvent
        The event to save
    database : IDatabase
        The database to save the event to

    Raises
    ------
    ValueError
        Raise error if name is already in use
    """
    database.events.save(event)


def save_timeseries_csv(
    name: str, event: IEvent, df: pd.DataFrame, database: IDatabase
) -> None:
    database.write_to_csv(name, event, df)


def edit_event(event: IEvent, database: IDatabase) -> None:
    database.events.edit(event)


def delete_event(name: str, database: IDatabase) -> None:
    database.events.delete(name)


def copy_event(
    old_name: str, database: IDatabase, new_name: str, new_description: str
) -> None:
    database.events.copy(old_name, new_name, new_description)


def download_wl_data(
    station_id, start_time, end_time, units: UnitTypesLength, file=None
) -> pd.DataFrame:
    return HistoricalNearshore.download_wl_data(
        station_id, start_time, end_time, units, file
    )


def read_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    return Event.read_csv(csvpath)


def plot_wl(
    event: IEvent, database: IDatabase, input_wl_df: pd.DataFrame = None
) -> str:
    return database.plot_wl(event, input_wl_df)


def plot_river(
    event: IEvent,
    database: IDatabase,
    input_river_df: list[pd.DataFrame],
) -> str:
    return database.plot_river(event, input_river_df)


def plot_rainfall(
    event: IEvent, database: IDatabase, input_rainfall_df: pd.DataFrame = None
) -> str:
    return database.plot_rainfall(event, input_rainfall_df)


def plot_wind(
    event: IEvent, database: IDatabase, input_wind_df: pd.DataFrame = None
) -> str:
    return database.plot_wind(event, input_wind_df)


def save_cyclone_track(event: IEvent, track: TropicalCyclone, database: IDatabase):
    database.write_cyc(event, track)


# Get a list of all public functions defined in this module
__all__ = [
    name
    for name, obj in globals().items()
    if (inspect.isfunction(obj) or isinstance(obj, types.FunctionType))
    and not name.startswith("_")
]

# Append 'IMeasure' to the list
__all__.append("IEvent")
