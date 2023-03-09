# from floodapat.object_model import ...
import pandas as pd


# upon start up of FloodAdapt
def read_database() -> (
    None
):  # read all toml files incl site config and populate Database class
    pass


def get_buildings():  # including all exposure data from the FIAT base model
    pass


def get_SFINCS_model():  # model grid, location of existing pumps, floodwalls etc
    pass


def get_aggregation_areas():
    pass


def get_event_templates() -> list():
    # get a list ideally automatically from the child classes of the parent class Event
    pass


def get_hazard_measure_types() -> list():
    pass


def get_impact_measure_types() -> list():
    pass
