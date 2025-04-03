# from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.interface.object_model import IObjectModel


class Scenario(IObjectModel):
    """BaseModel describing the expected variables and data types of a scenario."""

    event: str
    projection: str
    strategy: str
