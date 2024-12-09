from abc import abstractmethod
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from pydantic import BaseModel

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)


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
    _attrs_type = BenefitModel
    dir_name = ObjectDir.benefit
    display_name = "Benefit"

    results_path: Path
    scenarios: pd.DataFrame

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created."""
        ...

    @abstractmethod
    def run_cost_benefit(self):
        """Run the cost benefit analysis."""
        ...

    @abstractmethod
    def cba(self):
        """Return the cost benefit analysis results."""
        ...

    @abstractmethod
    def cba_aggregation(self):
        """Return the cost benefit analysis results."""
        ...

    @abstractmethod
    def get_output(self) -> dict[str, Any]:
        """Return the output of the cost benefit analysis."""
        ...

    @abstractmethod
    def has_run_check(self) -> bool:
        """Check if the benefit analysis has been run."""
        ...

    @abstractmethod
    def ready_to_run(self) -> bool:
        """Check if the benefit analysis is ready to run."""
        ...
