from abc import abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel

from flood_adapt.dbs_classes.path_builder import ObjectDir
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel


class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class BenefitModel(IObjectModel):
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


class IBenefit(IObject[BenefitModel]):
    attrs: BenefitModel
    dir_name = ObjectDir.benefit

    results_path: Path
    scenarios: pd.DataFrame
    has_run: bool = False

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created."""
        ...
