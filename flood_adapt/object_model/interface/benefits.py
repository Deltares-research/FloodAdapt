import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

import pandas as pd
from pydantic import BaseModel, validator


class CurrentSituationModel(BaseModel):
    projection: str
    year: int


class BenefitModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object"""

    name: str
    description: Optional[str] = ""
    lock_count: int = 0
    strategy: str
    event_set: str
    projection: str
    future_year: int
    current_situation: CurrentSituationModel
    baseline_strategy: str
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None

    @validator("lock_count")
    def validate_lock_count(cls, lock_count: int) -> int:
        """Validate lock_count"""
        if lock_count < 0:
            raise ValueError("lock_count must be a positive integer")
        return lock_count


class IBenefit(ABC):
    attrs: BenefitModel
    database_input_path: Union[str, os.PathLike]
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Benefit attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """get Benefit attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Benefit attributes to a toml file"""
        ...

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""
        ...
