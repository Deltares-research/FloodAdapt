from enum import Enum

from pydantic import BaseModel


class UnitTypesLength(str, Enum):
    meters = "meters"
    centimeters = "centimeters"
    millimeters = "millimeters"
    feet = "feet"
    inch = "inch"


class UnitTypesVelocity(str, Enum):
    meters = "m/s"
    knots = "knots"


class UnitTypesDischarge(str, Enum):
    cfs = "cfs"
    cms = "m3/s"


class UnitTypesIntensity(str, Enum):
    inch = "inch/hr"
    mm = "mm/hr"


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"


class UnitfulLength(BaseModel):
    value: float
    units: UnitTypesLength

    def convert(self, new_units: UnitTypesLength) -> float:
        """converts given length value different units

        Parameters
        ----------
        new_units : UnitTypesLength
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to meters
        if self.units == "centimeters":
            conversion = 1.0 / 100  # meters
        if self.units == "millimeters":
            conversion = 1.0 / 1000  # meters
        elif self.units == "meters":
            conversion = 1.0  # meters
        elif self.units == "feet":
            conversion = 1.0 / 3.28084  # meters
        elif self.units == "inch":
            conversion = 0.0254  # meters
        else:
            conversion = 1
        # second, convert to new units
        if new_units == "centimeters":
            new_conversion = 100.0
        if new_units == "millimeters":
            new_conversion = 1000.0
        elif new_units == "meters":
            new_conversion = 1.0
        elif new_units == "feet":
            new_conversion = 3.28084
        elif new_units == "inch":
            new_conversion = 1.0 / 0.0254
        else:
            new_conversion = 1
        return conversion * new_conversion * self.value


class UnitfulVelocity(BaseModel):
    value: float
    units: UnitTypesVelocity

    def convert(self, new_units: UnitTypesVelocity) -> float:
        """converts given  velocity to different units

        Parameters
        ----------
        new_units : UnitTypesVelocity
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to meters/second
        if self.units == "knots":
            conversion = 1.0 / 1.943844  # m/s
        elif self.units == "m/s":
            conversion = 1
        # second, convert to new units
        if new_units == "knots":
            new_conversion = 1.0
        elif new_units == "m/s":
            new_conversion = 1.943844
        return conversion * new_conversion * self.value


class UnitfulDirection(BaseModel):
    value: float
    units: str = "deg N"


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


class UnitfulDischarge(BaseModel):
    value: float
    units: UnitTypesDischarge

    def convert(self, new_units: UnitTypesDischarge) -> float:
        """converts given discharge to different units

        Parameters
        ----------
        new_units : UnitTypesDischarge
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to meters/second
        if self.units == "cfs":  # cubic feet per second
            conversion = 0.02832  # m3/s
        elif self.units == "m3/s":
            conversion = 1
        # second, convert to new units
        if new_units == "cfs":
            new_conversion = 1.0 / 0.02832
        elif new_units == "m3/s":
            new_conversion = 1.0
        return conversion * new_conversion * self.value


class UnitfulIntensity(BaseModel):
    value: float
    units: UnitTypesIntensity

    def convert(self, new_units: UnitTypesIntensity) -> float:
        """converts given rainfall intensity to different units

        Parameters
        ----------
        new_units : UnitTypesIntensity
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to meters/second
        if self.units == "inch/hr":  # cubic feet per second
            conversion = 25.4  # mm/hr
        elif self.units == "mm/hr":
            conversion = 1.0
        # second, convert to new units
        if new_units == "inch/hr":
            new_conversion = 1.0
        elif new_units == "mm/hr":
            new_conversion = 1.0 / 25.4
        return conversion * new_conversion * self.value
