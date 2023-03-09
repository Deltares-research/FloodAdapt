from enum import Enum

from pydantic import BaseModel


class UnitTypesLength(str, Enum):
    meters = "meters"
    centimeters = "centimeters"
    feet = "feet"
    inch = "inch"


class UnitTypesVelocity(str, Enum):
    meters = "m/s"
    centimeters = "knots"


class UnitTypesDischarge(str, Enum):
    cfs = "cfs"


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"


class UnitfulVelocity(BaseModel):
    value: float
    units: UnitTypesLength

    def convert_unit(self) -> float:
        """converts given velocity to meters per second

        Returns
        -------
        float
            converted parameter in meters per second
        """
        if self.units == "knots":
            conversion = 1.0 / 1.943844  # m/s
        else:
            conversion = 1
        return conversion * self.value


class UnitfulDirection(BaseModel):
    value: float
    units: str = "deg N"


class UnitfulDischarge(BaseModel):
    value: float
    units: UnitTypesDischarge

    def convert_unit(self) -> float:
        """converts given length value to cubic meters per second

        Returns
        -------
        float
            converted parameter in cubic meters per second
        """

        if self.units == "cfs":  # cubic feet per second
            conversion = 0.02832  # m3/s
        else:
            conversion = 1
        return self.value * conversion


class UnitfulLength(BaseModel):
    value: float
    units: UnitTypesLength

    def convert_unit(self) -> float:
        """converts given length value to meters

        Returns
        -------
        float
            converted parameter in meters
        """
        if self.units == "centimeters":
            conversion = 1.0 / 100  # meters
        elif self.units == "meters":
            conversion = 1.0  # meters
        elif self.units == "feet":
            conversion = 1.0 / 3.28084  # meters
        elif self.units == "inch":
            conversion = 0.025  # meters
        else:
            conversion = 1
        return conversion * self.value


class UnitfulRefValue(BaseModel):
    value: float
    units: str
    type: VerticalReference


class UnitfulValue(BaseModel):
    value: float
    units: UnitTypes

    def convert_unit(self) -> float:
        if self.units == "centimeters":
            conversion = 1.0 / 100  # meters
        elif self.units == "meters":
            conversion = 1.0  # meters
        elif self.units == "feet":
            conversion = 1.0 / 3.28084  # meters
        elif self.units == "inch":
            conversion = 25.4  # millimeters
        elif self.units == "knots":
            conversion = 1.0 / 1.943844  # m/s
        elif self.units == "cfs":  # cubic feet per second
            conversion = 0.02832  # m3/s
        else:
            conversion = 1
        return self.value * conversion


# def convert_unit(self) ->  float:
#     if self.units == 'centimeters':
#         conversion = 1./100 # meters
#     elif self.units == 'meters':
#         conversion = 1. # meters
#     elif self.units == 'feet':
#         conversion = 1./3.28084 # meters
#     elif self.units == 'inch':
#         conversion = 25.4 # millimeters
#     elif self.units == 'knots':
#         conversion = 1. / 1.943844  # m/s
#     elif self.units == 'cfs': # cubic feet per second
#         conversion = 0.02832 # m3/s
#     elif self.units == 'cms':
#         conversion = 1.  # m3/s
#     else:
#         conversion = None
#     return conversion
