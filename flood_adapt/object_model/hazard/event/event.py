from abc import ABC
from enum import Enum

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class Mode(str, Enum):
    """class describing the accepted input for the variable mode in Event"""

    single_scenario = "single_scenario"
    risk = "risk"


class Template(str, Enum):
    """class describing the accepted input for the variable template in Event"""

    Synthetic = "Synthetic"
    Hurricane = "Hurricane"


class Timing(str, Enum):
    """class describing the accepted input for the variable timng in Event"""

    historical = "historical"
    idealized = "idealized"


class EventModel(BaseModel):  # add WindModel etc as this is shared among all? templates
    """BaseModel describing the expected variables and data types of attributes common to all event types"""

    name: str
    long_name: str
    mode: Mode
    template: Template
    timing: Timing
    water_level_offset: UnitfulLength


class Event(ABC):
    """abstract parent class for all event types"""

    @staticmethod
    def generate_timeseries():
        ...
