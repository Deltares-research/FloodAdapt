# Event tab
import os
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_controller import IDatabase
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.interface.events import (
    IEvent,
)
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength


def get_events(database: IDatabase) -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return database.get_events()


def get_event(name: str, database: IDatabase) -> IEvent:
    return database.get_event(name)


def get_event_mode(name: str, database: IDatabase) -> str:
    filename = database.input_path / "events" / f"{name}" / f"{name}.toml"
    return EventFactory.get_mode(filename)


def create_event(attrs: dict[str, Any], database: IDatabase) -> IEvent:
    return EventFactory.load_dict(attrs, database.input_path)


def save_event_toml(event: IEvent, database: IDatabase) -> None:
    database.save_event(event)


def save_timeseries_csv(
    name: str, event: IEvent, df: pd.DataFrame, database: IDatabase
) -> None:
    database.write_to_csv(name, event, df)


def edit_event(event: IEvent, database: IDatabase) -> None:
    database.edit_event(event)


def delete_event(name: str, database: IDatabase) -> None:
    database.delete_event(name)


def copy_event(
    old_name: str, database: IDatabase, new_name: str, new_description: str
) -> None:
    database.copy_event(old_name, new_name, new_description)


def download_wl_data(
    station_id, start_time, end_time, units: UnitTypesLength
) -> pd.DataFrame:
    return Event.download_wl_data(station_id, start_time, end_time, units)


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
