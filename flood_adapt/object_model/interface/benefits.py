from typing import Optional

from pydantic import BaseModel

from flood_adapt.object_model.interface.object_model import IObjectModel


class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class Benefit(IObjectModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object."""

    strategy: str
    event_set: str
    projection: str
    future_year: int
    current_situation: CurrentSituationModel
    baseline_strategy: str
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None
