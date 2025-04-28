from typing import Optional

from pydantic import BaseModel

from flood_adapt.objects.object_model import Object


class CurrentSituationModel(BaseModel):
    """
    The accepted input for a current situation in FloodAdapt.

    Attributes
    ----------
    projection : str
        The name of the projection. Should be a projection saved in the database.
    year : int
        The year of the current situation.
    """

    projection: str
    year: int


class Benefit(Object):
    """BaseModel describing the expected variables and data types of a Benefit analysis object.

    Attributes
    ----------
    name: str
        The name of the benefit analysis.
    description: str
        The description of the benefit analysis. Defaults to "".
    strategy : str
        The name of the strategy. Should be a strategy saved in the database.
    event_set : str
        The name of the event set. Should be an event set saved in the database.
    projection : str
        The name of the projection. Should be a projection saved in the database.
    future_year : int
        The future year for the analysis.
    current_situation : CurrentSituationModel
        The current situation model.
    baseline_strategy : str
        The name of the baseline strategy.
    discount_rate : float
        The discount rate for the analysis.
    implementation_cost : Optional[float]
        The implementation cost of the strategy. Defaults to None.
    annual_maint_cost : Optional[float]
        The annual maintenance cost of the strategy. Defaults to None.
    """

    strategy: str
    event_set: str
    projection: str
    future_year: int
    current_situation: CurrentSituationModel
    baseline_strategy: str
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None
