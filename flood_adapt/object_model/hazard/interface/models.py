from datetime import datetime, timedelta

from pydantic import (
    BaseModel,
    field_serializer,
    field_validator,
)

REFERENCE_TIME = datetime(year=2021, month=1, day=1, hour=0, minute=0, second=0)


class TimeModel(BaseModel):
    start_time: datetime = REFERENCE_TIME
    end_time: datetime = REFERENCE_TIME + timedelta(days=1)
    time_step: timedelta = timedelta(minutes=10)

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

    @field_serializer("time_step")
    @classmethod
    def serialize_time_step(cls, value: timedelta) -> float:
        return value.total_seconds()
