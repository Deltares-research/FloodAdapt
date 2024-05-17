import os
from abc import ABC, abstractmethod
from typing import Any, Optional, Union
from enum import Enum

import pandas as pd
from pydantic import BaseModel


class TippingPointMetrics(str, Enum):
    """class describing the accepted input for the variable metric_type in TippingPoint"""

    # based on what I have found in floodadapt - but can be changed
    FloodedAll = "FloodedAll"
    FloodedLowVulnerability = "FloodedLowVulnerability"
    FloodedHighVulnerability = "FloodedHighVulnerability"
    TotalDamageEvent = "TotalDamageEvent"
    TotalResDamageEvent = "TotalResDamageEvent"
    ResidentialMinorCount = "ResidentialMinorCount"
    ResidentialMajorCount = "ResidentialMajorCount"
    ResidentialDestroyedCount = "ResidentialDestroyedCount"
    CommercialCount = "CommercialCount"
    CommercialMinorCount = "CommercialMinorCount"
    CommercialMajorCount = "CommercialMajorCount"
    CommercialDestroyedCount = "CommercialDestroyedCount"
    HealthCount = "HealthCount"
    HealthMinorCount = "HealthMinorCount"
    HealthMajorCount = "HealthMajorCount"
    HealthDestroyedCount = "HealthDestroyedCount"
    SchoolsCount = "SchoolsCount"
    SchoolsMinorCount = "SchoolsMinorCount"
    SchoolsMajorCount = "SchoolsMajorCount"
    SchoolsDestroyedCount = "SchoolsDestroyedCount"
    EmergencyCount = "EmergencyCount"
    EmergencyMinorCount = "EmergencyMinorCount"
    EmergencyMajorCount = "EmergencyMajorCount"
    EmergencyDestroyedCount = "EmergencyDestroyedCount"
    DisplacedLowVulnerability = "DisplacedLowVulnerability"
    DisplacedHighVulnerability = "DisplacedHighVulnerability"
    SlightlyFloodedRoads = "SlightlyFloodedRoads"
    MinorFloodedRoads = "MinorFloodedRoads"
    MajorFloodedRoads = "MajorFloodedRoads"
    FullyFloodedRoads = "FullyFloodedRoads"


class TippingPointStatus(str, Enum):
    """class describing the accepted input for the variable metric_type in TippingPoint"""

    reached = "reached"
    not_reached = "not_reached"
    completed = "completed"


class TippingPointOperator(str, Enum):
    """class describing the accepted input for the variable operator in TippingPoint"""

    greater = "greater"
    less = "less"


class TipPointModel(BaseModel):
    """BaseModel describing the expected variables and data types of a Tipping Point analysis object"""

    name: str
    description: Optional[str] = ""
    strategy: str
    event_set: str
    projection: str
    sealevelrise: list[float]  # could be a numpy array too
    tipping_point_metric: list[tuple[TippingPointMetrics, float, TippingPointOperator]]
    status: Optional[TippingPointStatus] = TippingPointStatus.not_reached


class ITipPoint(ABC):
    attrs: TipPointModel
    database_input_path: Union[str, os.PathLike]
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Tipping Point attributes from toml file"""
        ...

    @staticmethod  # copping from benefits.py
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get Tipping Point attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Tipping Point attributes to a toml file"""
        ...

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this tipping point calculation and if they have already been created"""
        ...
