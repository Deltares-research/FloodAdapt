# Event tab
import os
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_controller import Database
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
    Mode,
)
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength


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


def get_event(name: str) -> IEvent:
    """Get a benefit from the database by name.

    Parameters
    ----------
    name : str
        The name of the benefit to retrieve.

    Returns
    -------
    IBenefit
        The benefit object with the given name.

    Raises
    ------
    ValueError
        If the benefit with the given name does not exist.
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
    filename = Database().events.get_database_path() / f"{name}" / f"{name}.toml"
    return Event.get_mode(filename)


def create_synthetic_event(attrs: dict[str, Any]) -> ISynthetic:
    """Create a synthetic event object from a dictionary of attributes.

    Parameters
    ----------
    attrs : dict[str, Any]
        Dictionary of attributes. Should adhere to the SyntheticEventModel schema.

    Returns
    -------
    Synthetic
        Synthetic event object
    """
    return EventFactory.get_event("Synthetic").load_dict(attrs)


def create_historical_nearshore_event(attrs: dict[str, Any]) -> IHistoricalNearshore:
    """Create a historical nearshore event object from a dictionary of attributes.

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
    """Create a historical offshore event object from a dictionary of attributes.

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
    """Create a historical hurricane event object from a dictionary of attributes.

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


def save_event_toml(event: IEvent) -> None:
    """Save an event object to the database.

    Parameters
    ----------
    event : IEvent
        The event object to save.

    Raises
    ------
    ValueError
        If the event object is not valid.
    """
    Database().events.save(event)


def save_timeseries_csv(name: str, event: IEvent, df: pd.DataFrame) -> None:
    """Save timeseries data to a csv file.

    Parameters
    ----------
    name : str
        Name of the event
    event : IEvent
        Event object
    df : pd.DataFrame
        Dataframe of timeseries data
    """
    Database().write_to_csv(name, event, df)


def edit_event(event: IEvent) -> None:
    """Edit an event object in the database.

    Parameters
    ----------
    event : IEvent
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


def download_wl_data(
    station_id, start_time, end_time, units: UnitTypesLength, source: str, file=None
) -> pd.DataFrame:
    """Download water level data from a station or tide gauge.

    Parameters
    ----------
    station_id : str
        Station ID
    start_time : str
        Start time of data
    end_time : str
        End time of data
    units : UnitTypesLength
        Units of data
    source : str
        Source of data. Should be one of `ndbc` or `noaa_coops`
    """
    return HistoricalNearshore.download_wl_data(
        station_id, start_time, end_time, units, source, file
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
    return Event.read_csv(csvpath)


def plot_wl(event: IEvent, input_wl_df: pd.DataFrame = None) -> str:
    """Plot water level data for an event.

    Parameters
    ----------
    event : IEvent
        The event object
    input_wl_df : pd.DataFrame
        DataFrame containing water level data

    Returns
    -------
    str
        Path to the created html plot
    """
    return Database().plot_wl(event, input_wl_df)


def plot_river(
    event: IEvent,
    input_river_df: list[pd.DataFrame],
) -> str:
    """Plot river discharge data for an event.

    Parameters
    ----------
    event : IEvent
        The event object
    input_river_df : pd.DataFrame
        DataFrame containing discharge data

    Returns
    -------
    str
        Path to the created html plot
    """
    return Database().plot_river(event, input_river_df)


def plot_rainfall(event: IEvent, input_rainfall_df: pd.DataFrame = None) -> str:
    """Plot rainfall data for an event.

    Parameters
    ----------
    event : IEvent
        The event object
    input_rainfall_df : pd.DataFrame
        DataFrame containing rainfall data

    Returns
    -------
    str
        Path to the created html plot
    """
    return Database().plot_rainfall(event, input_rainfall_df)


def plot_wind(event: IEvent, input_wind_df: pd.DataFrame = None) -> str:
    """Plot wind data for an event.

    Parameters
    ----------
    event : IEvent
        The event object
    input_wind_df : pd.DataFrame
        DataFrame containing wind data

    Returns
    -------
    str
        Path to the created html plot
    """
    return Database().plot_wind(event, input_wind_df)


def save_cyclone_track(event: IEvent, track: TropicalCyclone):
    """Save cyclone track data to the event folder.

    Parameters
    ----------
    event : IEvent
        The event object
    track : TropicalCyclone
        The cyclone track data
    """
    Database().write_cyc(event, track)
