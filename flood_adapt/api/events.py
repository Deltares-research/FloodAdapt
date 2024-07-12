# Event tab
import os
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

import flood_adapt.dbs_controller as db
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.historical import HistoricalEvent
from flood_adapt.object_model.hazard.interface.events import IEvent, IEventModel
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength


def get_events() -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return db.Database().events.list_objects()


def get_event(name: str) -> IEvent:
    return db.Database().events.get(name)


def get_event_mode(name: str) -> str:
    filename = db.Database().events.get_database_path() / f"{name}" / f"{name}.toml"
    return EventFactory.get_mode(filename)


def create_event(attrs: dict[str, Any] | IEventModel) -> IEvent:
    """Create a event object from a dictionary of attributes.

    Parameters
    ----------
    attrs : IEventModel [str, Any]
        Dictionary of attributes

    Returns
    -------
    IEvent
        Depending on attrs.template an event object.
        Can be of type: Synthetic, Historical_nearshore, Historical_offshore, or Historical_hurricane.
    """
    return EventFactory.load_dict(attrs)


def save_event_toml(event: IEvent) -> None:
    db.Database().events.save(event)


def save_timeseries_csv(name: str, event: IEvent, df: pd.DataFrame) -> None:
    db.Database().write_to_csv(name, event, df)


def edit_event(event: IEvent) -> None:
    db.Database().events.edit(event)


def delete_event(name: str) -> None:
    db.Database().events.delete(name)


def copy_event(old_name: str, new_name: str, new_description: str) -> None:
    db.Database().events.copy(old_name, new_name, new_description)


def download_wl_data(
    station_id, start_time, end_time, units: UnitTypesLength, source: str, file=None
) -> pd.DataFrame:
    return HistoricalEvent.download_wl_data(
        station_id, start_time, end_time, units, source, file
    )


def read_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    return IEvent.read_csv(csvpath)


def plot_wl(event: IEvent, input_wl_df: pd.DataFrame = None) -> str:
    return db.Database().plot_wl(event, input_wl_df)


def plot_river(
    event: IEvent,
    input_river_df: list[pd.DataFrame],
) -> str:
    return db.Database().plot_river(event, input_river_df)


def plot_rainfall(event: IEvent, input_rainfall_df: pd.DataFrame = None) -> str:
    return db.Database().plot_rainfall(event, input_rainfall_df)


def plot_wind(event: IEvent, input_wind_df: pd.DataFrame = None) -> str:
    return db.Database().plot_wind(event, input_wind_df)


def save_cyclone_track(event: IEvent, track: TropicalCyclone):
    db.Database().write_cyc(event, track)
