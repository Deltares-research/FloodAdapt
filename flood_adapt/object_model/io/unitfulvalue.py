import math
from enum import Enum

from pydantic import BaseModel, field_validator


class Unit(str, Enum):
    """
    Represents a unit of measurement.
    """

    pass


class ValueUnitPair(BaseModel):
    """
    Represents a value with associated units.

    Attributes:
        value (float): The numerical value.
        units (Unit): The units of the value.
    """

    value: float
    units: Unit

    def __init__(self, value: float, units: Unit, **data):
        super().__init__(value=value, units=units, **data)

    def convert(self, new_units: Unit) -> "ValueUnitPair":
        raise NotImplementedError

    def __str__(self):
        return f"{self.value} {self.units.value}"

    def __sub__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(self.value - other.convert(self.units).value, self.units)

    def __add__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(self.value + other.convert(self.units).value, self.units)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return math.isclose(
            self.value, other.convert(self.units).value, rel_tol=1e-2
        )  # 1% relative tolerance for equality. So 1.0 == 1.01 evaluates to True

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value < other.convert(self.units).value

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value > other.convert(self.units).value

    def __ge__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return (self > other) or (self == other)

    def __le__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return (self < other) or (self == other)

    def __ne__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return not (self == other)

    def __mul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(self.value / other, self.units)
        else:
            raise TypeError(
                f"Cannot multiply self: {type(self).__name__} with other: {type(other).__name__}. Only int and float are allowed."
            )

    def __div__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(self.value / other, self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units).value
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )

    def __truediv__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(self.value / other, self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units).value
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )


class UnitTypesLength(Unit):
    meters = "meters"
    centimeters = "centimeters"
    millimeters = "millimeters"
    feet = "feet"
    inch = "inch"
    miles = "miles"


class UnitTypesArea(Unit):
    m2 = "m2"
    cm2 = "cm2"
    mm2 = "mm2"
    sf = "sf"


class UnitTypesVolume(Unit):
    m3 = "m3"
    cf = "cf"


class UnitTypesVelocity(Unit):
    mps = "m/s"
    knots = "knots"
    mph = "mph"


class UnitTypesDirection(Unit):
    degrees = "deg N"


class UnitTypesTime(Unit):
    seconds = "seconds"
    minutes = "minutes"
    hours = "hours"
    days = "days"


class UnitTypesDischarge(Unit):
    cfs = "cfs"
    cms = "m3/s"


class UnitTypesIntensity(Unit):
    inch_hr = "inch/hr"
    mm_hr = "mm/hr"


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"


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
        if self.units == UnitTypesLength.meters:
            conversion = 1.0  # meters
        elif self.units == UnitTypesLength.centimeters:
            conversion = 1.0 / 100  # meters
        elif self.units == UnitTypesLength.millimeters:
            conversion = 1.0 / 1000  # meters
        elif self.units == UnitTypesLength.feet:
            conversion = 1.0 / 3.28084  # meters
        elif self.units == UnitTypesLength.inch:
            conversion = 0.0254  # meters
        elif self.units == UnitTypesLength.miles:
            conversion = 1609.344  # meters
        else:
            raise TypeError("Invalid length units")
        # second, convert to new units
        if new_units == UnitTypesLength.centimeters:
            new_conversion = 100.0
        elif new_units == UnitTypesLength.millimeters:
            new_conversion = 1000.0
        elif new_units == UnitTypesLength.meters:
            new_conversion = 1.0
        elif new_units == UnitTypesLength.feet:
            new_conversion = 3.28084
        elif new_units == UnitTypesLength.inch:
            new_conversion = 1.0 / 0.0254
        elif new_units == UnitTypesLength.miles:
            new_conversion = 1.0 / 1609.344
        else:
            raise TypeError("Invalid length units")
        return UnitfulLength(conversion * new_conversion * self.value, new_units)

    @field_validator("value")
    @classmethod
    def length_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Length cannot be negative: {value}")
        return value


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


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
        if self.units == UnitTypesArea.cm2:
            conversion = 1.0 / 10000  # meters
        elif self.units == UnitTypesArea.mm2:
            conversion = 1.0 / 1000000  # meters
        elif self.units == UnitTypesArea.m2:
            conversion = 1.0  # meters
        elif self.units == UnitTypesArea.sf:
            conversion = 1.0 / 10.764  # meters
        else:
            raise TypeError("Invalid area units")

        # second, convert to new units
        if new_units == UnitTypesArea.cm2:
            new_conversion = 10000.0
        elif new_units == UnitTypesArea.mm2:
            new_conversion = 1000000.0
        elif new_units == UnitTypesArea.m2:
            new_conversion = 1.0
        elif new_units == UnitTypesArea.sf:
            new_conversion = 10.764
        else:
            raise TypeError("Invalid area units")
        return UnitfulArea(conversion * new_conversion * self.value, new_units)

    @field_validator("value")
    @classmethod
    def area_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Area cannot be negative: {value}")
        return value


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
        if self.units == UnitTypesVelocity.knots:
            conversion = 1.0 / 1.943844  # m/s
        elif self.units == UnitTypesVelocity.mps:
            conversion = 1
        elif self.units == UnitTypesVelocity.mph:
            conversion = 0.44704
        else:
            raise TypeError("Invalid velocity units")
        # second, convert to new units
        if new_units == UnitTypesVelocity.knots:
            new_conversion = 1.943844
        elif new_units == UnitTypesVelocity.mps:
            new_conversion = 1.0
        elif new_units == UnitTypesVelocity.mph:
            new_conversion = 2.236936
        else:
            raise TypeError("Invalid velocity units")
        return UnitfulVelocity(conversion * new_conversion * self.value, new_units)

    @field_validator("value")
    @classmethod
    def velocity_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Velocity cannot be negative: {value}")
        return value


class UnitfulDirection(ValueUnitPair):
    value: float
    units: UnitTypesDirection

    @field_validator("value")
    @classmethod
    def direction_must_be_between_0_360(cls, value: float):
        if not (0 <= value <= 360):
            raise ValueError(
                f"Direction must be in degrees, between 0 and 360: {value}"
            )
        return value


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
        if self.units == UnitTypesDischarge.cfs:  # cubic feet per second
            conversion = 0.02832  # m3/s
        elif self.units == UnitTypesDischarge.cms:
            conversion = 1
        else:
            raise TypeError("Invalid discharg units")
        # second, convert to new units
        if new_units == UnitTypesDischarge.cfs:
            new_conversion = 1.0 / 0.02832
        elif new_units == UnitTypesDischarge.cms:
            new_conversion = 1.0
        else:
            raise TypeError("Invalid discharge units")

        return UnitfulDischarge(conversion * new_conversion * self.value, new_units)

    @field_validator("value")
    @classmethod
    def discharge_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Discharge cannot be negative: {value}")
        return value


class UnitfulIntensity(ValueUnitPair):
    value: float
    units: UnitTypesIntensity

    def convert(self, new_units: UnitTypesIntensity) -> "UnitfulIntensity":
        conversion_factors = {
            UnitTypesIntensity.inch_hr: {
                UnitTypesIntensity.inch_hr: 1.0,
                UnitTypesIntensity.mm_hr: 25.39544832,
            },
            UnitTypesIntensity.mm_hr: {
                UnitTypesIntensity.inch_hr: 1.0 / 25.39544832,
                UnitTypesIntensity.mm_hr: 1.0,
            },
        }

        if self.units not in conversion_factors or new_units not in conversion_factors:
            raise TypeError("Invalid time units")

        conversion_factor = conversion_factors[self.units][new_units]
        return UnitfulIntensity(self.value * conversion_factor, new_units)

    @field_validator("value")
    @classmethod
    def intensity_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Intensity cannot be negative: {value}")
        return value


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
        if self.units == UnitTypesVolume.cf:  # cubic feet
            conversion = 0.02831685  # m3
        elif self.units == UnitTypesVolume.m3:
            conversion = 1.0
        # second, convert to new units
        if new_units == UnitTypesVolume.cf:
            new_conversion = 1.0 / 0.02831685
        elif new_units == UnitTypesVolume.m3:
            new_conversion = 1.0
        return UnitfulVolume(conversion * new_conversion * self.value, new_units)

    @field_validator("value")
    @classmethod
    def volume_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Volume cannot be negative: {value}")
        return value


class UnitfulTime(ValueUnitPair):
    value: float
    units: UnitTypesTime

    def convert(self, new_units: UnitTypesTime) -> "UnitfulTime":
        """converts given time to different units

        Parameters
        ----------
        new_units : UnitTypesTime
            units to be converted to

        Returns
        -------
        float
            converted value
        """
        conversion_factors = {
            UnitTypesTime.days: {
                UnitTypesTime.days: 1.0,
                UnitTypesTime.hours: 24.0,
                UnitTypesTime.minutes: 24.0 * 60.0,
                UnitTypesTime.seconds: 24.0 * 60.0 * 60.0,
            },
            UnitTypesTime.hours: {
                UnitTypesTime.days: 1.0 / 24.0,
                UnitTypesTime.hours: 1.0,
                UnitTypesTime.minutes: 60.0,
                UnitTypesTime.seconds: 60.0 * 60.0,
            },
            UnitTypesTime.minutes: {
                UnitTypesTime.days: 1.0 / (24.0 * 60.0),
                UnitTypesTime.hours: 1.0 / 60.0,
                UnitTypesTime.minutes: 1.0,
                UnitTypesTime.seconds: 60.0,
            },
            UnitTypesTime.seconds: {
                UnitTypesTime.days: 1.0 / (24.0 * 60.0 * 60.0),
                UnitTypesTime.hours: 1.0 / (60.0 * 60.0),
                UnitTypesTime.minutes: 1.0 / 60.0,
                UnitTypesTime.seconds: 1.0,
            },
        }

        if self.units not in conversion_factors or new_units not in conversion_factors:
            raise TypeError("Invalid time units")

        conversion_factor = conversion_factors[self.units][new_units]
        return UnitfulTime(self.value * conversion_factor, new_units)
