# Event tab

from typing import Any

from flood_adapt.dbs_controller import IDatabase
from flood_adapt.object_model.hazard.event.synthetic import Synthetic
from flood_adapt.object_model.interface.events import IEvent, ISynthetic


def get_events(database: IDatabase) -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return database.get_events()


def get_event(name: str, database: IDatabase) -> IEvent:
    return database.get_event(name)


def create_synthetic_event(attrs: dict[str, Any], database: IDatabase) -> ISynthetic:
    return Synthetic.load_dict(attrs)


def save_synthetic_event(event: ISynthetic, database: IDatabase) -> None:
    database.save_synthetic_event(event)


def edit_synthetic_event(event: ISynthetic, database: IDatabase) -> None:
    database.edit_synthetic_event(event)


def delete_event(name: str, database: IDatabase) -> None:
    database.delete_event(name)


def copy_event(
    old_name: str, database: IDatabase, new_name: str, new_long_name: str
) -> None:
    database.copy_event(old_name, new_name, new_long_name)


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
