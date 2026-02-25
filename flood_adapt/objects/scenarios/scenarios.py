from pydantic import field_validator

from flood_adapt.objects.object_model import Object


class Scenario(Object):
    """BaseModel describing the expected variables and data types of a scenario.

    A scenario is a combination of an event, a projection, and a strategy, that all should be saved in the database.

    Attributes
    ----------
    event : str
        The name of the event. Must not be empty.
    projection : str
        The name of the projection. Must not be empty.
    strategy : str
        The name of the strategy. Must not be empty.

    """

    event: str
    projection: str
    strategy: str

    @field_validator("event", "projection", "strategy")
    @classmethod
    def validate_names(
        cls,
        value: str,
    ) -> str:
        cls._validate_name_format(value)
        return value
