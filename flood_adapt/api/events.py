# Event tab

from typing import Any

from flood_adapt.dbs_controller import IDatabase
from flood_adapt.object_model.hazard.event.synthetic import HistoricalNearshore
from flood_adapt.object_model.interface.events import IHistoricalNearshore


def get_events(database: IDatabase) -> dict[str, Any]:
    # use PyQt table / sorting and filtering either with PyQt table or in the API
    return database.get_events()


def create_historical_nearshore_event(
    attrs: dict[str, Any], database: IDatabase
) -> IHistoricalNearshore:
    return HistoricalNearshore.load_dict(attrs)


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
