import os
from abc import abstractmethod
from typing import Any, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from flood_adapt.object_model.interface.database_user import IDatabaseUser


class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class BenefitModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object."""

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


class IBenefit(IDatabaseUser):
    attrs: BenefitModel
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Benefit attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """Get Benefit attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Benefit attributes to a toml file."""
        ...

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created."""
        ...

    @abstractmethod
    def run_cost_benefit(self):
        """Run the cost benefit analysis."""
        ...
