import math
from datetime import timedelta
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Unit(str, Enum):
    """Represent a unit of measurement."""

    pass


class IUnitFullValue(BaseModel):
    """
    Represents a value with associated units.

    Attributes
    ----------
        _STANDARD_UNIT (Unit): The default unit.
        _CONVERSION_FACTORS (dict[Unit: float]): A dictionary of conversion factors from any unit to the default unit.
        value (float): The numerical value.
        units (Unit): The units of the value.
    """

    _DEFAULT_UNIT: Unit
    _CONVERSION_FACTORS: dict[Unit:float]
    value: float
    units: Unit

    def convert(self, new_units: Unit) -> float:
        """Return the value converted to the new units.

        Args:
            new_units (Unit): The new units.

        Returns
        -------
            float: The converted value.
        """
        if new_units not in self._CONVERSION_FACTORS:
            raise ValueError(f"Invalid units: {new_units}")
        in_default_units = self.value * self._CONVERSION_FACTORS[self.units]
        return in_default_units / self._CONVERSION_FACTORS[new_units]

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


class UnitfulLength(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesLength.meters: 1.0,
        UnitTypesLength.centimeters: 100.0,
        UnitTypesLength.millimeters: 1000.0,
        UnitTypesLength.feet: 3.28084,
        UnitTypesLength.inch: 1.0 / 0.0254,
        UnitTypesLength.miles: 1609.344,
    }
    _DEFAULT_UNIT = UnitTypesLength.meters
    value: float
    units: UnitTypesLength


class UnitfulHeight(UnitfulLength):
    value: float = Field(gt=0.0)


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


class UnitfulArea(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesArea.m2: 10_000,
        UnitTypesArea.cm2: 10_000,
        UnitTypesArea.mm2: 1_000_000,
        UnitTypesArea.sf: 10.764,
    }
    _DEFAULT_UNIT = UnitTypesArea.mm2
    value: float
    units: UnitTypesArea

    @field_validator("value")
    @classmethod
    def area_cannot_be_negative(cls, value: float):
        if value < 0:
            raise ValueError(f"Area cannot be negative: {value}")
        return value


class UnitfulVelocity(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesVelocity.mph: 2.236936,
        UnitTypesVelocity.mps: 1,
        UnitTypesVelocity.knots: 1.943844,
    }
    _DEFAULT_UNIT = UnitTypesVelocity.mps

    value: float = Field(gt=0.0)
    units: UnitTypesVelocity


class UnitfulDirection(IUnitFullValue):
    value: float = Field(gt=0.0, le=360.0)
    units: UnitTypesDirection


class UnitfulDischarge(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesDischarge.cfs: 0.02832,
        UnitTypesDischarge.cms: 1,
    }
    _DEFAULT_UNIT = UnitTypesDischarge.cms

    value: float = Field(gt=0.0)
    units: UnitTypesDischarge


class UnitfulIntensity(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesIntensity.inch_hr: 25.39544832,
        UnitTypesIntensity.mm_hr: 1,
    }
    _DEFAULT_UNIT = UnitTypesIntensity.mm_hr

    value: float = Field(gt=0.0)
    units: UnitTypesIntensity


class UnitfulVolume(IUnitFullValue):
    _CONVERSION_FACTORS = {
        UnitTypesVolume.m3: 1.0,
        UnitTypesVolume.cf: 35.3147,
    }
    _DEFAULT_UNIT = UnitTypesVolume.m3

    value: float = Field(gt=0.0)
    units: UnitTypesVolume


class UnitfulTime(IUnitFullValue):
    value: float
    units: UnitTypesTime

    _CONVERSION_FACTORS = {
        UnitTypesTime.hours: {
            UnitTypesTime.days: 1.0 / 24.0,
            UnitTypesTime.hours: 1.0,
            UnitTypesTime.minutes: 60.0,
            UnitTypesTime.seconds: 60.0 * 60.0,
        },
    }
    _DEFAULT_UNIT = UnitTypesTime.hours

    def to_timedelta(self) -> timedelta:
        """Convert given time to datetime.deltatime object, relative to UnitfulTime(0, Any).

        Returns
        -------
        datetime.timedelta
            datetime.timedelta object with representation: (days, seconds, microseconds)
        """
        seconds = self.convert(UnitTypesTime.seconds).value
        return timedelta(seconds=seconds)
