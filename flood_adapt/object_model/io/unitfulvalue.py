from enum import Enum

from pydantic import BaseModel


class UnitTypesLength(str, Enum):
    meters = "meters"
    centimeters = "centimeters"
    millimeters = "millimeters"
    feet = "feet"
    inch = "inch"
    miles = "miles"


class UnitTypesArea(str, Enum):
    m2 = "m2"
    cm2 = "cm2"
    mm2 = "mm2"
    sf = "sf"


class UnitTypesVolume(str, Enum):
    m3 = "m3"
    cf = "cf"


class UnitTypesVelocity(str, Enum):
    meters = "m/s"
    knots = "knots"
    mph = "mph"


class UnitTypesDirection(str, Enum):
    degrees = "deg N"


class UnitTypesDischarge(str, Enum):
    cfs = "cfs"
    cms = "m3/s"


class UnitTypesIntensity(str, Enum):
    inch = "inch/hr"
    mm = "mm/hr"


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"


class ValueUnitPair(BaseModel):
    value: float
    units: str

    def __str__(self):
        return f"{self.value} {self.units}"


class UnitfulLength(ValueUnitPair):
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
        elif self.units == "miles":
            conversion = 1609.344  # meters
        else:
            ValueError("Invalid length units")
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
        elif self.units == "miles":
            new_conversion = 1.0 / 1609.344
        else:
            ValueError("Invalid length units")
        return conversion * new_conversion * self.value


class UnitfulArea(ValueUnitPair):
    value: float
    units: UnitTypesArea

    def convert(self, new_units: UnitTypesArea) -> float:
        """converts given length value different units

        Parameters
        ----------
        new_units : UnitTypesArea
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to meters
        if self.units == "cm2":
            conversion = 1.0 / 10000  # meters
        if self.units == "mm2":
            conversion = 1.0 / 1000000  # meters
        elif self.units == "m2":
            conversion = 1.0  # meters
        elif self.units == "sf":
            conversion = 1.0 / 10.764  # meters
        else:
            conversion = 1.0

        # second, convert to new units
        if new_units == "cm2":
            new_conversion = 10000.0
        if new_units == "mm2":
            new_conversion = 1000000.0
        elif new_units == "m2":
            new_conversion = 1.0
        elif new_units == "sf":
            new_conversion = 10.764
        else:
            new_conversion = 1
        return conversion * new_conversion * self.value


class UnitfulVelocity(ValueUnitPair):
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
        elif self.units == "mph":
            conversion = 0.44704
        else:
            ValueError("Invalid velocity units")
        # second, convert to new units
        if new_units == "knots":
            new_conversion = 1.943844
        elif new_units == "m/s":
            new_conversion = 1.0
        elif new_units == "mph":
            new_conversion = 2.236936
        else:
            ValueError("Invalid velocity units")
        return conversion * new_conversion * self.value


class UnitfulDirection(ValueUnitPair):
    value: float
    units: UnitTypesDirection


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


class UnitfulDischarge(ValueUnitPair):
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
        else:
            ValueError("Invalid discharg units")
        # second, convert to new units
        if new_units == "cfs":
            new_conversion = 1.0 / 0.02832
        elif new_units == "m3/s":
            new_conversion = 1.0
        else:
            ValueError("Invalid discharg units")

        return conversion * new_conversion * self.value


class UnitfulIntensity(ValueUnitPair):
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
        else:
            ValueError("Invalid rainfall intensity units")
        # second, convert to new units
        if new_units == "inch/hr":
            new_conversion = 1.0 / 25.4
        elif new_units == "mm/hr":
            new_conversion = 1.0
        else:
            ValueError("Invalid rainfall intensity units")
        return conversion * new_conversion * self.value


class UnitfulVolume(ValueUnitPair):
    value: float
    units: UnitTypesVolume

    def convert(self, new_units: UnitTypesVolume) -> float:
        """converts given volume to different units

        Parameters
        ----------
        new_units : UnitTypesVolume
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        # first, convert to m3
        if self.units == "cf":  # cubic feet
            conversion = 0.02831685  # m3
        elif self.units == "m3":
            conversion = 1.0
        # second, convert to new units
        if new_units == "cf":
            new_conversion = 1.0 / 0.02831685
        elif new_units == "m3":
            new_conversion = 1.0
        return conversion * new_conversion * self.value
