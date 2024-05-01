import os
from abc import abstractmethod
from typing import Optional, Union

import pandas as pd
from pydantic import BaseModel
from .objectModel import ObjectModel, IObject



class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class BenefitModel(ObjectModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object"""

    strategy: str
    event_set: str
    projection: str
    future_year: int
    current_situation: CurrentSituationModel
    baseline_strategy: str
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None


class IBenefit(IObject):
    attrs: BenefitModel
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""
        ...
