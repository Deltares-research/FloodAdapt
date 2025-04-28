from datetime import datetime, timedelta

from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
)

from flood_adapt.objects.forcing import unit_system as us

REFERENCE_TIME = datetime(year=2021, month=1, day=1, hour=0, minute=0, second=0)


class TimeFrame(BaseModel):
    """
    Class representing a time frame for a simulation.

    Attributes
    ----------
    start_time : datetime
        The start time of the simulation.
    end_time : datetime
        The end time of the simulation.
    time_step : timedelta
        The time step of the simulation. Default is calculated as 1/1000 of the duration.
    """

    start_time: datetime = REFERENCE_TIME
    end_time: datetime = REFERENCE_TIME + timedelta(days=1)

    @property
    def time_step(self) -> timedelta:
        return self._time_step

    @field_validator("start_time", "end_time", mode="before")
    @classmethod
    def try_parse_datetime(cls, value: str | datetime) -> datetime:
        SUPPORTED_DATETIME_FORMATS = [
            "%Y%m%d %H%M%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S.%f%z",
        ]
        if not isinstance(value, datetime):
            for fmt in SUPPORTED_DATETIME_FORMATS:
                try:
                    value = datetime.strptime(value, fmt)
                    break
                except Exception:
                    pass

        if not isinstance(value, datetime):
            raise ValueError(
                f"Could not parse start time: {value}. Supported formats are {', '.join(SUPPORTED_DATETIME_FORMATS)}"
            )
        return value

    @model_validator(mode="after")
    def start_time_before_end_time(self):
        if self.start_time >= self.end_time:
            raise ValueError(
                f"Start time: {self.start_time} must be before end time: {self.end_time}"
            )
        return self

    @model_validator(mode="after")
    def dynamic_timestep(self):
        num_intervals = 1000
        time_span = (self.end_time - self.start_time).total_seconds()

        # Round the time step to the second for simplicity
        self._time_step = timedelta(
            seconds=int(timedelta(seconds=time_span / num_intervals).total_seconds())
        )
        return self

    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    def duration_as_unitfultime(
        self, unit: us.UnitTypesTime = us.UnitTypesTime.hours
    ) -> us.UnitfulTime:
        return us.UnitfulTime(
            value=(self.duration).total_seconds(),
            units=us.UnitTypesTime.seconds,
        ).transform(unit)

    def __str__(self) -> str:
        return f"{self.start_time} - {self.end_time}"
