from typing import Optional

from pydantic import BaseModel, Field


class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class BenefitModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object"""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    strategy: str
    event_set: str
    projection: str
    future_year: int
    current_situation: CurrentSituationModel
    baseline_strategy: str
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None