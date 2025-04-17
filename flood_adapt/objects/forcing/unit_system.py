import enum
import math
from abc import ABC
from datetime import timedelta
from enum import Enum
from typing import Generic, Optional, Type, TypeVar, Union

from pydantic import BaseModel, Field, model_validator

__all__ = [
    "ValueUnitPair",
    "VerticalReference",
    "UnitTypesLength",
    "UnitTypesArea",
    "UnitTypesVolume",
    "UnitTypesVelocity",
    "UnitTypesDirection",
    "UnitTypesTime",
    "UnitTypesDischarge",
    "UnitTypesIntensity",
    "UnitfulLength",
    "UnitfulHeight",
    "UnitfulLengthRefValue",
    "UnitfulArea",
    "UnitfulVelocity",
    "UnitfulDirection",
    "UnitfulDischarge",
    "UnitfulIntensity",
    "UnitfulVolume",
    "UnitfulTime",
    "ValueUnitPairs",
]

TUnit = TypeVar("TUnit", bound=enum.Enum)
TClass = TypeVar("TClass", bound="ValueUnitPair")


class ValueUnitPair(ABC, BaseModel, Generic[TUnit]):
    """
    Represents a value with associated units.

    Attributes
    ----------
    value: float
        The numerical value.
    units : Unit
        The units of the value.
    """

    _DEFAULT_UNIT: TUnit
    _CONVERSION_FACTORS: dict[TUnit, float]

    value: float
    units: TUnit

    def convert(self, new_units: TUnit) -> float:
        """Return the value converted to the new units.

        Parameters
        ----------
        new_units : Unit
            The new units.

        Returns
        -------
        converted_value : float
            The converted value.
        """
        if new_units not in self._CONVERSION_FACTORS:
            raise ValueError(f"Invalid units: {new_units}")
        in_default_units = self.value / self._CONVERSION_FACTORS[self.units]
        return in_default_units * self._CONVERSION_FACTORS[new_units]

    def transform(self: TClass, new_units: TUnit) -> TClass:
        """Return a new ValueUnitPair instance with the value converted to the new units.

        Parameters
        ----------
        new_units : Unit
            The new units.

        Returns
        -------
        value_unit_pair : ValueUnitPair
            The new ValueUnitPair instance with the value converted to the new units and the new units.
        """
        return type(self)(value=self.convert(new_units), units=new_units)

    @model_validator(mode="before")
    @classmethod
    def extract_unit_class(cls, data: Optional[dict]) -> "ValueUnitPair":
        if cls is not ValueUnitPair:
            return data  # Already in the right subclass, don't interfere

        if not isinstance(data, dict):
            raise TypeError("Expected dictionary for deserialization.")

        str_unit = data.get("units")
        if not str_unit:
            raise ValueError("Missing 'units' field in input data.")

        for unit_enum_cls, vu_cls in UNIT_TO_CLASS.items():
            try:
                enum_unit = unit_enum_cls(str_unit)
                data["units"] = enum_unit
                return vu_cls(**data)
            except ValueError:
                continue

        raise ValueError(f"Unsupported or unknown unit: {str_unit}")

    def __str__(self) -> str:
        return f"{self.value} {self.units.value}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}(value={self.value}, units={self.units})"

    def __sub__(self: TClass, other: TClass) -> TClass:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(
            value=self.value - other.convert(self.units), units=self.units
        )

    def __add__(self: TClass, other: TClass) -> TClass:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(
            value=self.value + other.convert(self.units), units=self.units
        )

    def __eq__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, ValueUnitPair):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        if not (hasattr(other, "value") and hasattr(other, "units")):
            raise AttributeError(f"Incomplete UnitfulValue instance: {other}")

        if not isinstance(other.units, type(self.units)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )

        return math.isclose(
            self.value, other.convert(self.units), rel_tol=1e-2
        )  # 1% relative tolerance for equality. So 1.0 == 1.01 evaluates to True

    def __lt__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value < other.convert(self.units)

    def __gt__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value > other.convert(self.units)

    def __ge__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return (self > other) or (self == other)

    def __le__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return (self < other) or (self == other)

    def __ne__(self: TClass, other: TClass) -> bool:
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return not (self == other)

    def __mul__(self: TClass, other: int | float) -> TClass:
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(value=self.value * other, units=self.units)
        else:
            raise TypeError(
                f"Cannot multiply self: {type(self).__name__} with other: {type(other).__name__}. Only int and float are allowed."
            )

    def __div__(self: TClass, other: TClass | int | float) -> TClass | float:
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(value=self.value / other, units=self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units)
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )

    def __truediv__(self: TClass, other: TClass | int | float) -> TClass | float:
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(value=self.value / other, units=self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units)
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )


class UnitTypesLength(str, Enum):
    """Units of length.

    Attributes
    ----------
    meters : meters
    centimeters : centimeters
    millimeters : millimeters
    feet : feet
    inch : inch
    miles : miles
    """

    meters = "meters"
    centimeters = "centimeters"
    millimeters = "millimeters"
    feet = "feet"
    inch = "inch"
    miles = "miles"


class UnitTypesArea(str, Enum):
    """Units of area.

    Attributes
    ----------
    m2 : square meters
    dm2 : square decimeters
    cm2 : square centimeters
    mm2 : square millimeters
    sf : square feet
    """

    m2 = "m2"
    dm2 = "dm2"
    cm2 = "cm2"
    mm2 = "mm2"
    sf = "sf"


class UnitTypesVolume(str, Enum):
    """Units of volume.

    Attributes
    ----------
    m3 : cubic meters
    cf : cubic feet
    """

    m3 = "m3"
    cf = "cf"


class UnitTypesVelocity(str, Enum):
    """Units of velocity.

    Attributes
    ----------
    mps : meters per second
    knots : nautical miles per hour
    mph : miles per hour
    """

    mps = "m/s"
    knots = "knots"
    mph = "mph"


class UnitTypesDirection(str, Enum):
    """Units of direction.

    Attributes
    ----------
    degrees : degrees
    """

    degrees = "deg N"


class UnitTypesTime(str, Enum):
    """Units of time.

    Attributes
    ----------
    seconds : seconds
    minutes : minutes
    hours : hours
    days : days
    """

    seconds = "seconds"
    minutes = "minutes"
    hours = "hours"
    days = "days"


class UnitTypesDischarge(str, Enum):
    """Units of discharge.

    Attributes
    ----------
    cfs : cubic feet per second
    cms : cubic meters per second
    """

    cfs = "cfs"
    cms = "m3/s"


class UnitTypesIntensity(str, Enum):
    """Units of intensity.

    Attributes
    ----------
    inch_hr : inch per hour
    mm_hr : millimeter per hour
    """

    inch_hr = "inch/hr"
    mm_hr = "mm/hr"


class VerticalReference(str, Enum):
    """Vertical reference for height.

    Attributes
    ----------
    floodmap : Use the floodmap as reference.
    datum : Use the datum as reference.
    """

    floodmap = "floodmap"
    datum = "datum"


class UnitfulLength(ValueUnitPair[UnitTypesLength]):
    """Combination of length and unit.

    Attributes
    ----------
    value : float
        The length value.
    units : UnitTypesLength
        The unit of length.
    """

    _CONVERSION_FACTORS: dict[UnitTypesLength, float] = {
        UnitTypesLength.meters: 1.0,
        UnitTypesLength.centimeters: 100.0,
        UnitTypesLength.millimeters: 1000.0,
        UnitTypesLength.feet: 3.28084,
        UnitTypesLength.inch: 1.0 / 0.0254,
        UnitTypesLength.miles: 1 / 1609.344,
    }
    _DEFAULT_UNIT: UnitTypesLength = UnitTypesLength.meters


class UnitfulHeight(UnitfulLength):
    """Combination of height and unit.

    Attributes
    ----------
    value : float
        The height value, must be greater than or equal to 0.
    units : UnitTypesLength
        The unit of height.
    """

    value: float = Field(ge=0.0)


class UnitfulLengthRefValue(UnitfulLength):
    """Combination of length and unit with a reference value.

    Attributes
    ----------
    value : float
        The length value, must be greater than or equal to 0.
    units : UnitTypesLength
        The unit of length.
    type : VerticalReference
        The vertical reference for the length.
    """

    type: VerticalReference


class UnitfulArea(ValueUnitPair[UnitTypesArea]):
    """Combination of area and unit.

    Attributes
    ----------
    value : float
        The area value, must be greater than or equal to 0.
    units : UnitTypesArea
            The unit of area.

    """

    _CONVERSION_FACTORS: dict[UnitTypesArea, float] = {
        UnitTypesArea.m2: 1,
        UnitTypesArea.dm2: 100,
        UnitTypesArea.cm2: 10_000,
        UnitTypesArea.mm2: 1_000_000,
        UnitTypesArea.sf: 10.764,
    }
    _DEFAULT_UNIT: UnitTypesArea = UnitTypesArea.m2
    value: float = Field(ge=0.0)


class UnitfulVelocity(ValueUnitPair[UnitTypesVelocity]):
    """Combination of velocity and unit.

    Attributes
    ----------
    value : float
        The velocity value, must be greater than or equal to 0.
    units : UnitTypesVelocity
        The unit of velocity.
    """

    _CONVERSION_FACTORS: dict[UnitTypesVelocity, float] = {
        UnitTypesVelocity.mph: 2.236936,
        UnitTypesVelocity.mps: 1,
        UnitTypesVelocity.knots: 1.943844,
    }
    _DEFAULT_UNIT: UnitTypesVelocity = UnitTypesVelocity.mps
    value: float = Field(ge=0.0)


class UnitfulDirection(ValueUnitPair[UnitTypesDirection]):
    """Combination of direction and unit.

    Attributes
    ----------
    value : float
        The direction value, must be greater than or equal to 0 and less than or equal to 360.
    units : UnitTypesDirection
        The unit of direction.
    """

    _CONVERSION_FACTORS: dict[UnitTypesDirection, float] = {
        UnitTypesDirection.degrees: 1.0,
    }
    _DEFAULT_UNIT: UnitTypesDirection = UnitTypesDirection.degrees

    value: float = Field(ge=0.0, le=360.0)


class UnitfulDischarge(ValueUnitPair[UnitTypesDischarge]):
    """Combination of discharge and unit.

    Attributes
    ----------
    value : float
        The discharge value, must be greater than or equal to 0.
    units : UnitTypesDischarge
            The unit of discharge.
    """

    _CONVERSION_FACTORS: dict[UnitTypesDischarge, float] = {
        UnitTypesDischarge.cfs: 35.314684921034,
        UnitTypesDischarge.cms: 1,
    }
    _DEFAULT_UNIT: UnitTypesDischarge = UnitTypesDischarge.cms

    value: float = Field(ge=0.0)


class UnitfulIntensity(ValueUnitPair[UnitTypesIntensity]):
    """Combination of intensity and unit.

    Attributes
    ----------
    value : float
        The intensity value, must be greater than or equal to 0.
    units : UnitTypesIntensity
        The unit of intensity.
    """

    _CONVERSION_FACTORS: dict[UnitTypesIntensity, float] = {
        UnitTypesIntensity.inch_hr: 1 / 25.39544832,
        UnitTypesIntensity.mm_hr: 1,
    }
    _DEFAULT_UNIT: UnitTypesIntensity = UnitTypesIntensity.mm_hr
    value: float = Field(ge=0.0)


class UnitfulVolume(ValueUnitPair[UnitTypesVolume]):
    """Combination of volume and unit.

    Attributes
    ----------
    value : float
        The volume value, must be greater than or equal to 0.
    units : UnitTypesVolume
            The unit of volume.
    """

    _CONVERSION_FACTORS: dict[UnitTypesVolume, float] = {
        UnitTypesVolume.m3: 1.0,
        UnitTypesVolume.cf: 35.3146667,
    }
    _DEFAULT_UNIT: UnitTypesVolume = UnitTypesVolume.m3

    value: float = Field(ge=0.0)


class UnitfulTime(ValueUnitPair[UnitTypesTime]):
    """Combination of time and unit.

    Attributes
    ----------
    value : float
        The time value.
    units : UnitTypesTime
        The unit of time.
    """

    _CONVERSION_FACTORS: dict[UnitTypesTime, float] = {
        UnitTypesTime.days: 1.0 / 24.0,
        UnitTypesTime.hours: 1.0,
        UnitTypesTime.minutes: 60.0,
        UnitTypesTime.seconds: 60.0 * 60.0,
    }
    _DEFAULT_UNIT: UnitTypesTime = UnitTypesTime.hours

    @staticmethod
    def from_timedelta(td: timedelta) -> "UnitfulTime":
        """Convert given timedelta to UnitfulTime object."""
        return UnitfulTime(value=td.total_seconds(), units=UnitTypesTime.seconds)

    def to_timedelta(self) -> timedelta:
        """Convert given time to datetime.deltatime object, relative to UnitfulTime(0, Any).

        Returns
        -------
        datetime.timedelta
            datetime.timedelta object with representation: (days, seconds, microseconds)
        """
        return timedelta(seconds=self.convert(UnitTypesTime.seconds))


ValueUnitPairs = Union[
    UnitfulLength,
    UnitfulTime,
    UnitfulDischarge,
    UnitfulDirection,
    UnitfulVelocity,
    UnitfulIntensity,
    UnitfulArea,
    UnitfulVolume,
]

UNIT_TO_CLASS: dict[enum.EnumMeta, Type[ValueUnitPairs]] = {
    UnitTypesLength: UnitfulLength,
    UnitTypesTime: UnitfulTime,
    UnitTypesDischarge: UnitfulDischarge,
    UnitTypesDirection: UnitfulDirection,
    UnitTypesVelocity: UnitfulVelocity,
    UnitTypesIntensity: UnitfulIntensity,
    UnitTypesArea: UnitfulArea,
    UnitTypesVolume: UnitfulVolume,
}
