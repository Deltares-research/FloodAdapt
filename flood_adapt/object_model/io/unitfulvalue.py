import math
from datetime import timedelta
from enum import Enum

from pydantic import BaseModel, Field


class Unit(str, Enum):
    """Represent a unit of measurement."""

    pass


class IUnitFullValue(BaseModel):
    """
    Represents a value with associated units.

    Frozen class attributes:
    ------------------------
        CONVERSION_FACTORS (dict[Unit: float]): A dictionary of conversion factors from the default unit to any unit.
        DEFAULT_UNIT (Unit): The default unit.

    Instance attributes:
    --------------------
        value (float): The numerical value.
        units (Unit): The units of the value.
    """

    DEFAULT_UNIT: Unit = Field(frozen=True, exclude=True, default=None)
    CONVERSION_FACTORS: dict[Unit, float] = Field(frozen=True, exclude=True, default={})

    value: float
    units: Unit

    def __init__(self, *args, **kwargs):
        if type(self) is IUnitFullValue:
            raise TypeError(
                "IUnitFullValue is an abstract class and cannot be instantiated directly."
            )
        if args and len(args) == 2:
            value, units = args
            super().__init__(value=value, units=units, **kwargs)
        else:
            super().__init__(*args, **kwargs)

    def convert(self, new_units: Unit) -> float:
        """Return the value converted to the new units.

        Args:
            new_units (Unit): The new units.

        Returns
        -------
            float: The converted value.
        """
        if new_units not in self.CONVERSION_FACTORS:
            raise ValueError(f"Invalid units: {new_units}")
        in_default_units = self.value / self.CONVERSION_FACTORS[self.units]
        return in_default_units * self.CONVERSION_FACTORS[new_units]

    def __str__(self):
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
        if not isinstance(other, IUnitFullValue):
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
            return type(self)(self.value / other, self.units)
        else:
            raise TypeError(
                f"Cannot multiply self: {type(self).__name__} with other: {type(other).__name__}. Only int and float are allowed."
            )

    def __div__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            return type(self)(self.value / other, self.units)
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
    CONVERSION_FACTORS: dict[UnitTypesLength, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesLength.meters: 1.0,
            UnitTypesLength.centimeters: 100.0,
            UnitTypesLength.millimeters: 1000.0,
            UnitTypesLength.feet: 3.28084,
            UnitTypesLength.inch: 1.0 / 0.0254,
            UnitTypesLength.miles: 1 / 1609.344,
        },
    )
    DEFAULT_UNIT: UnitTypesLength = Field(
        frozen=True, exclude=True, default=UnitTypesLength.meters
    )

    value: float
    units: UnitTypesLength


class UnitfulHeight(UnitfulLength):
    value: float = Field(gt=0.0)


class UnitfulLengthRefValue(UnitfulLength):
    type: VerticalReference


class UnitfulArea(IUnitFullValue):
    CONVERSION_FACTORS: dict[UnitTypesArea, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesArea.m2: 10_000,
            UnitTypesArea.cm2: 10_000,
            UnitTypesArea.mm2: 1_000_000,
            UnitTypesArea.sf: 10.764,
        },
    )
    DEFAULT_UNIT: UnitTypesArea = Field(
        frozen=True, exclude=True, default=UnitTypesArea.mm2
    )

    value: float = Field(gt=0.0)
    units: UnitTypesArea


class UnitfulVelocity(IUnitFullValue):
    CONVERSION_FACTORS: dict[UnitTypesVelocity, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesVelocity.mph: 2.236936,
            UnitTypesVelocity.mps: 1,
            UnitTypesVelocity.knots: 1.943844,
        },
    )
    DEFAULT_UNIT: UnitTypesVelocity = Field(
        frozen=True, exclude=True, default=UnitTypesVelocity.mps
    )

    value: float = Field(gt=0.0)
    units: UnitTypesVelocity


class UnitfulDirection(IUnitFullValue):
    value: float = Field(gt=0.0, le=360.0)
    units: UnitTypesDirection


class UnitfulDischarge(IUnitFullValue):
    CONVERSION_FACTORS: dict[UnitTypesDischarge, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesDischarge.cfs: 0.02832,
            UnitTypesDischarge.cms: 1,
        },
    )
    DEFAULT_UNIT: UnitTypesDischarge = Field(
        frozen=True, exclude=True, default=UnitTypesDischarge.cms
    )

    value: float = Field(gt=0.0)
    units: UnitTypesDischarge


class UnitfulIntensity(IUnitFullValue):
    CONVERSION_FACTORS: dict[UnitTypesIntensity, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesIntensity.inch_hr: 1 / 25.39544832,
            UnitTypesIntensity.mm_hr: 1,
        },
    )
    DEFAULT_UNIT: UnitTypesIntensity = Field(
        frozen=True, exclude=True, default=UnitTypesIntensity.mm_hr
    )

    value: float = Field(gt=0.0)
    units: UnitTypesIntensity


class UnitfulVolume(IUnitFullValue):
    CONVERSION_FACTORS: dict[UnitTypesVolume, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesVolume.m3: 1.0,
            UnitTypesVolume.cf: 35.3147,
        },
    )
    DEFAULT_UNIT: UnitTypesVolume = Field(
        frozen=True, exclude=True, default=UnitTypesVolume.m3
    )

    value: float = Field(gt=0.0)
    units: UnitTypesVolume


class UnitfulTime(IUnitFullValue):
    value: float
    units: UnitTypesTime

    CONVERSION_FACTORS: dict[UnitTypesTime, float] = Field(
        frozen=True,
        exclude=True,
        default={
            UnitTypesTime.days: 1.0 / 24.0,
            UnitTypesTime.hours: 1.0,
            UnitTypesTime.minutes: 60.0,
            UnitTypesTime.seconds: 60.0 * 60.0,
        },
    )
    DEFAULT_UNIT: UnitTypesTime = Field(
        frozen=True, exclude=True, default=UnitTypesTime.hours
    )

    def to_timedelta(self) -> timedelta:
        """Convert given time to datetime.deltatime object, relative to UnitfulTime(0, Any).

        Returns
        -------
        datetime.timedelta
            datetime.timedelta object with representation: (days, seconds, microseconds)
        """
        return timedelta(seconds=self.convert(UnitTypesTime.seconds))
