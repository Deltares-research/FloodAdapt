from pydantic import BaseModel
from enum import Enum

class UnitTypes(str, Enum):
    meters = "meters"
    centimeters = "centimeters"
    cms = "cms" # cubic meter /second
    mps = "m/s" # meter/second
    feet = "feet"
    inch = "inch"
    cfs = "cfs"
    knots = "knots"
    degN = "degN"
        
    def convert_unit(unit) ->  float:
        if unit == 'centimeters':
            conversion = 1./100 # meters
        elif unit == 'meters':
            conversion = 1. # meters
        elif unit == 'feet':
            conversion = 1./3.28084 # meters
        elif unit == 'inch':
            conversion = 25.4 # millimeters
        elif unit == 'knots':
            conversion = 1. / 1.943844  # m/s
        elif unit == 'cfs': # cubic feet per second
            conversion = 0.02832 # m3/s
        elif unit == 'cms':
            conversion = 1.  # m3/s
        else:
            conversion = None
        return conversion


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"

class UnitfulValue(BaseModel):
    value: float
    units: UnitTypes

class UnitfulRefValue(BaseModel):
    value: float
    units: str
    type: VerticalReference