import enum
import math
from abc import ABC
from datetime import timedelta
from enum import Enum
from typing import Generic, Optional, Type, TypeVar

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
]

TUnit = TypeVar("TUnit", bound=enum.Enum)


class ValueUnitPair(BaseModel, ABC, Generic[TUnit]):
    """
    Represents a value with associated units.

    Frozen class attributes:
    ------------------------
        _CONVERSION_FACTORS (dict[Unit: float]): A dictionary of conversion factors from the default unit to any unit.
        _DEFAULT_UNIT (Unit): The default unit.

    Instance attributes:
    --------------------
        value (float): The numerical value.
        units (Unit): The units of the value.
    """

    _DEFAULT_UNIT: TUnit
    _CONVERSION_FACTORS: dict[TUnit, float]

    value: float
    units: TUnit

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def convert(self, new_units: TUnit) -> float:
        """Return the value converted to the new units.

        Args:
            new_units (str): The new units.

        Returns
        -------
            float: The converted value.
        """
        if new_units not in self._CONVERSION_FACTORS:
            raise ValueError(f"Invalid units: {new_units}")
        in_default_units = self.value / self._CONVERSION_FACTORS[self.units]
        return in_default_units * self._CONVERSION_FACTORS[new_units]

    @model_validator(mode="before")
    @classmethod
    def extract_unit_class(cls, data: Optional[dict]) -> dict:
        UNITS: dict[Type, Type] = {
            UnitTypesLength: UnitfulLength,
            UnitTypesTime: UnitfulTime,
            UnitTypesDischarge: UnitfulDischarge,
            UnitTypesDirection: UnitfulDirection,
            UnitTypesVelocity: UnitfulVelocity,
            UnitTypesIntensity: UnitfulIntensity,
            UnitTypesArea: UnitfulArea,
            UnitTypesVolume: UnitfulVolume,
        }
        if data is None or isinstance(
            data,
            ValueUnitPair,
        ):
            # Sometimes the data is already a ValueUnitPair instance, so no need to validate
            # If it is None, dont raise an error here and let the caller handle it
            return data

        if data.get("units") is None:
            raise ValueError("No units provided")

        unit_enum = None
        str_unit = data.get("units")
        for unit_types_enum in UNITS:
            try:
                unit_enum = unit_types_enum(str_unit)
                data["units"] = unit_enum
                return data
            except Exception:
                continue

        raise ValueError(f"Unsupported unit: {str_unit}")

    def __str__(self) -> str:
        return f"{self.value} {self.units.value}"

    def __repr__(self) -> str:
        return self.__str__()

    def __sub__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(
            value=self.value - other.convert(self.units), units=self.units
        )

    def __add__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return type(self)(
            value=self.value + other.convert(self.units), units=self.units
        )

    def __eq__(self, other):
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

    def __lt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value < other.convert(self.units)

    def __gt__(self, other):
        if not isinstance(other, type(self)):
            raise TypeError(
                f"Cannot compare self: {type(self).__name__} to other: {type(other).__name__}"
            )
        return self.value > other.convert(self.units)

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
            return type(self)(value=self.value * other, units=self.units)
        else:
            raise TypeError(
                f"Cannot multiply self: {type(self).__name__} with other: {type(other).__name__}. Only int and float are allowed."
            )

    def __div__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(value=self.value / other, units=self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units)
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )

    def __truediv__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(value=self.value / other, units=self.units)
        elif isinstance(other, type(self)):
            return self.value / other.convert(self.units)
        else:
            raise TypeError(
                f"Cannot divide self: {type(self).__name__} with other: {type(other).__name__}. Only {type(self).__name__}, int and float are allowed."
            )


class UnitTypesLength(str, Enum):
    meters = "meters"
    centimeters = "centimeters"
    millimeters = "millimeters"
    feet = "feet"
    inch = "inch"
    miles = "miles"


class UnitTypesArea(str, Enum):
    m2 = "m2"
    dm2 = "dm2"
    cm2 = "cm2"
    mm2 = "mm2"
    sf = "sf"


class UnitTypesVolume(str, Enum):
    m3 = "m3"
    cf = "cf"


class UnitTypesVelocity(str, Enum):
    mps = "m/s"
    knots = "knots"
    mph = "mph"


class UnitTypesDirection(str, Enum):
    degrees = "deg N"


class UnitTypesTime(str, Enum):
    seconds = "seconds"
    minutes = "minutes"
    hours = "hours"
    days = "days"


class UnitTypesDischarge(str, Enum):
    cfs = "cfs"
    cms = "m3/s"


class UnitTypesIntensity(str, Enum):
    inch_hr = "inch/hr"
    mm_hr = "mm/hr"


class VerticalReference(str, Enum):
    floodmap = "floodmap"
    datum = "datum"


class UnitfulLength(ValueUnitPair[UnitTypesLength]):
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
    value: float = Field(ge=0.0)


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


class UnitfulArea(ValueUnitPair[UnitTypesArea]):
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
    _CONVERSION_FACTORS: dict[UnitTypesVelocity, float] = {
        UnitTypesVelocity.mph: 2.236936,
        UnitTypesVelocity.mps: 1,
        UnitTypesVelocity.knots: 1.943844,
    }
    _DEFAULT_UNIT: UnitTypesVelocity = UnitTypesVelocity.mps
    value: float = Field(ge=0.0)


class UnitfulDirection(ValueUnitPair[UnitTypesDirection]):
    _CONVERSION_FACTORS: dict[UnitTypesDirection, float] = {
        UnitTypesDirection.degrees: 1.0,
    }
    _DEFAULT_UNIT: UnitTypesDirection = UnitTypesDirection.degrees

    value: float = Field(ge=0.0, le=360.0)


class UnitfulDischarge(ValueUnitPair[UnitTypesDischarge]):
    _CONVERSION_FACTORS: dict[UnitTypesDischarge, float] = {
        UnitTypesDischarge.cfs: 35.314684921034,
        UnitTypesDischarge.cms: 1,
    }
    _DEFAULT_UNIT: UnitTypesDischarge = UnitTypesDischarge.cms

    value: float = Field(ge=0.0)


class UnitfulIntensity(ValueUnitPair[UnitTypesIntensity]):
    _CONVERSION_FACTORS: dict[UnitTypesIntensity, float] = {
        UnitTypesIntensity.inch_hr: 1 / 25.39544832,
        UnitTypesIntensity.mm_hr: 1,
    }
    _DEFAULT_UNIT: UnitTypesIntensity = UnitTypesIntensity.mm_hr
    value: float = Field(ge=0.0)


class UnitfulVolume(ValueUnitPair[UnitTypesVolume]):
    _CONVERSION_FACTORS: dict[UnitTypesVolume, float] = {
        UnitTypesVolume.m3: 1.0,
        UnitTypesVolume.cf: 35.3146667,
    }
    _DEFAULT_UNIT: UnitTypesVolume = UnitTypesVolume.m3

    value: float = Field(ge=0.0)


class UnitfulTime(ValueUnitPair[UnitTypesTime]):
    _CONVERSION_FACTORS: dict[UnitTypesTime, float] = {
        UnitTypesTime.days: 1.0 / 24.0,
        UnitTypesTime.hours: 1.0,
        UnitTypesTime.minutes: 60.0,
        UnitTypesTime.seconds: 60.0 * 60.0,
    }
    _DEFAULT_UNIT: UnitTypesTime = UnitTypesTime.hours

    @staticmethod
    def from_timedelta(td: timedelta) -> "UnitfulTime":
        return UnitfulTime(value=td.total_seconds(), units=UnitTypesTime.seconds)

    def to_timedelta(self) -> timedelta:
        """Convert given time to datetime.deltatime object, relative to UnitfulTime(0, Any).

        Returns
        -------
        datetime.timedelta
            datetime.timedelta object with representation: (days, seconds, microseconds)
        """
        return timedelta(seconds=self.convert(UnitTypesTime.seconds))
