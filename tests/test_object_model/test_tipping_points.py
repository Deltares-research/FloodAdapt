import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import tomli
from flood_adapt.api.static import read_database
from flood_adapt.config import set_system_folder

from flood_adapt.object_model.tipping_point import TippingPoint
from flood_adapt.object_model.interface.tipping_points import ITipPoint


@pytest.fixture
def setup_database():
    # Mock the database setup or configure a test database
    read_database(
        rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database",
        "charleston_full",
    )
    set_system_folder(
        rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database\\system"
    )


def test_tipping_point_creation(setup_database):
    # Setup
    tp_dict = {
        "name": "tipping_point_test",
        "description": "",
        "event_set": "extreme12ft",
        "strategy": "no_measures",
        "projection": "current",
        "sealevelrise": [0.5, 1.0, 1.5],
        "tipping_point_metric": [
            ("FloodedAll", 34195.0, "greater"),
            ("FullyFloodedRoads", 2000, "greater"),
        ],
    }
    # Exercise
    test_point = TippingPoint.load_dict(tp_dict)
    test_point.create_tp_scenarios()

    # Verify
    assert test_point is not None
    assert isinstance(test_point, TippingPoint)


def test_run_scenarios(setup_database):
    tp_dict = {
        "name": "tipping_point_test",
        "description": "",
        "event_set": "extreme12ft",
        "strategy": "no_measures",
        "projection": "current",
        "sealevelrise": [0.5, 1.0, 1.5],
        "tipping_point_metric": [
            ("FloodedAll", 34195.0, "greater"),
            ("FullyFloodedRoads", 2000, "greater"),
        ],
    }
    test_point = TippingPoint.load_dict(tp_dict)
    test_point.create_tp_scenarios()
    # This should run without raising an exception
    test_point.run_tp_scenarios()


# database = read_database(
#     rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database",
#     "charleston_full",
# )
# set_system_folder(
#     rf"C:\\Users\\morenodu\\OneDrive - Stichting Deltares\\Documents\\GitHub\\FloodAdapt-Database\\system"
# )

# tp_dict = {
#     "name": "tipping_point_test",
#     "description": "",
#     "event_set": "extreme12ft",
#     "strategy": "no_measures",
#     "projection": "current",
#     "sealevelrise": [0.5, 1.0, 1.5],
#     "tipping_point_metric": [
#         ("FloodedAll", 34195.0, "greater"),
#         ("FullyFloodedRoads", 2000, "greater"),
#     ],
# }
# # load
# test_point = TippingPoint.load_dict(tp_dict)
# # create scenarios for tipping points
# test_point.create_tp_scenarios()
# # run all scenarios
# test_point.run_tp_scenarios()
