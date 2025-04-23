from flood_adapt.objects.object_model import Object


class Scenario(Object):
    """BaseModel describing the expected variables and data types of a scenario.

    A scenario is a combination of an event, a projection, and a strategy, that all should be saved in the database.

    Attributes
    ----------
    event : str
        The name of the event.
    projection : str
        The name of the projection.
    strategy : str
        The name of the strategy.

    """

    event: str
    projection: str
    strategy: str
