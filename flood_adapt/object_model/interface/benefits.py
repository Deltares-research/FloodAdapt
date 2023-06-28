import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union

from pydantic import BaseModel


class BenefitModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Benefit analysis object"""

    name: str
    description: Optional[str] = ""
    event_set: str
    strategy_future: str
    strategy_current: Optional[str] = "no_measures"
    projection_future: str
    projection_current: Optional[str] = "current"
    year_future: int
    year_current: int  # TODO is this user input or we have a default based on site.toml?
    discount_rate: float
    implementation_cost: Optional[float] = None
    annual_maint_cost: Optional[float] = None


class IBenefit(ABC):
    attrs: BenefitModel

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
    def check_scenarios(self):
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""
        ...
