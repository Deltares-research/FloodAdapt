# Event tab
import os
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_controller import Database
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import (
    EventFactory,
    HistoricalHurricane,
    HistoricalNearshore,
    HistoricalOffshore,
    IEvent,
    Synthetic,
)
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength


def get_events() -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return Database().events.list_objects()


def get_event(name: str) -> IEvent:
    return Database().events.get(name)


def get_event_mode(name: str) -> str:
    filename = Database().events.input_path / f"{name}" / f"{name}.toml"
    return Event.get_mode(filename)


def create_synthetic_event(attrs: dict[str, Any]) -> Synthetic:
    """Create a synthetic event object from a dictionary of attributes.

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


def create_historical_nearshore_event(attrs: dict[str, Any]) -> HistoricalNearshore:
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


def create_historical_offshore_event(attrs: dict[str, Any]) -> HistoricalOffshore:
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


def create_historical_hurricane_event(attrs: dict[str, Any]) -> HistoricalHurricane:
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


def save_event(event: IEvent) -> None:
    Database().events.save(event)


def save_event_toml(event: IEvent) -> None:
    Database().events.save(event)


def save_timeseries_csv(name: str, event: IEvent, df: pd.DataFrame) -> None:
    Database().write_to_csv(name, event, df)


def edit_event(event: IEvent) -> None:
    Database().events.edit(event)


def delete_event(name: str) -> None:
    Database().events.delete(name)


def copy_event(old_name: str, new_name: str, new_description: str) -> None:
    Database().events.copy(old_name, new_name, new_description)


def download_wl_data(
    station_id, start_time, end_time, units: UnitTypesLength, source: str, file=None
) -> pd.DataFrame:
    return HistoricalNearshore.download_wl_data(
        station_id, start_time, end_time, units, source, file
    )


def read_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    return Event.read_csv(csvpath)


def plot_wl(event: IEvent, input_wl_df: pd.DataFrame = None) -> str:
    return Database().plot_wl(event, input_wl_df)


def plot_river(
    event: IEvent,
    input_river_df: list[pd.DataFrame],
) -> str:
    return Database().plot_river(event, input_river_df)


def plot_rainfall(event: IEvent, input_rainfall_df: pd.DataFrame = None) -> str:
    return Database().plot_rainfall(event, input_rainfall_df)


def plot_wind(event: IEvent, input_wind_df: pd.DataFrame = None) -> str:
    return Database().plot_wind(event, input_wind_df)


def save_cyclone_track(event: IEvent, track: TropicalCyclone):
    Database().write_cyc(event, track)
