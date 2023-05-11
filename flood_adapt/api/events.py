# Event tab

import os
from typing import Any, Union

import pandas as pd

from flood_adapt.dbs_controller import IDatabase
from flood_adapt.object_model.hazard.event.historical_nearshore import (
    HistoricalNearshore,
)
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.interface.events import (
    IEvent,
    IHistoricalNearshore,
    ISynthetic,
)


def get_events(database: IDatabase) -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return database.get_events()


def get_event(name: str, database: IDatabase) -> IEvent:
    return database.get_event(name)


def create_synthetic_event(attrs: dict[str, Any]) -> ISynthetic:
    return Synthetic.load_dict(attrs)


def create_historical_nearshore_event(attrs: dict[str, Any]) -> IHistoricalNearshore:
    return HistoricalNearshore.load_dict(attrs)


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
    old_name: str, database: IDatabase, new_name: str, new_long_name: str
) -> None:
    database.copy_event(old_name, new_name, new_long_name)


def download_wl_data(station_id, start_time, end_time) -> pd.DataFrame:
    return HistoricalNearshore.download_wl_data(station_id, start_time, end_time)


def read_wl_csv(csvpath: Union[str, os.PathLike]) -> pd.DataFrame:
    return HistoricalNearshore.read_wl_csv(csvpath)


def plot_wl(event: IEvent, database: IDatabase) -> str:
    return database.plot_wl(event)


# def get_event(name: str) -> dict():  # get attributes
#     pass


# # on click add event
# def create_new_event(template: str) -> dict():  # get attributes
#     pass


# def set_event(event: dict):  # set attributes
#     pass


# # in event pop-up window on click OK
# def save_event(name: str):
#     pass


# # on click hurricane:
# def get_hurricane_tracks():
#     pass


# # on click historical from nearshore:
# def create_historical_nearshore_event() -> (
#     dict()
# ):  # gives back empty  object to populate pop-up window, different options for discharge are in the class #TODO: ask Julian
#     pass


# # on click plot water level boundary
# def get_waterlevel_timeseries(event: dict) -> dict():
#     pass


# # on click plot rainfall
# def get_rainfall_timeseries(event: dict):
#     pass


# # on click delete event
# def check_delete_event() -> (
#     bool
# ):  # , str: # str contains full error message, empty if False
#     pass


# # on click copy event
# def copy_event(name_orig: str, name_copy: str):
#     pass
