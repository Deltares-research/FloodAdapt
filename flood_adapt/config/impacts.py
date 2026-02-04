from enum import Enum
from typing import Optional

from pydantic import BaseModel


class FloodmapType(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class BenefitsModel(BaseModel):
    """The accepted input for the variable benefits in Site.

    Attributes
    ----------
    current_year : int
        The current year used in benefits calculations.
    current_projection : str
        The current projection used in benefits calculations.
    baseline_strategy : str
        The baseline strategy used in benefits calculations.
    event_set : str
        The event set used in benefits calculations.
    """

    current_year: int
    current_projection: str
    baseline_strategy: str
    event_set: str


class EquityModel(BaseModel):
    """
    The accepted input for the variable equity in Site.

    Attributes
    ----------
    census_data : str
        TODO
    percapitaincome_label : Optional[str], default="PerCapitaIncome"
        TODO
    totalpopulation_label : Optional[str], default="TotalPopulation"
        TODO
    """

    census_data: str
    percapitaincome_label: Optional[str] = "PerCapitaIncome"
    totalpopulation_label: Optional[str] = "TotalPopulation"


class AggregationModel(BaseModel):
    """The accepted input for the variable aggregation in Site.

    Attributes
    ----------
    name : str
        TODO
    file : str
        TODO
    field_name : str
        TODO
    equity : Optional[EquityModel], default=None
        TODO
    """

    name: str
    file: str
    field_name: str
    equity: Optional[EquityModel] = None


class BFEModel(BaseModel):
    """The accepted input for the variable bfe in Site.

    Attributes
    ----------
    geom : str
        TODO
    table : Optional[str], default=None
        TODO
    field_name : str
        TODO
    """

    geom: str
    table: Optional[str] = None
    field_name: str


class SVIModel(BaseModel):
    """The accepted input for the variable svi in Site.

    Attributes
    ----------
    geom : str
        TODO
    field_name : str
        TODO
    """

    geom: str
    field_name: str


class NoFootprintsModel(BaseModel):
    """
    The configuration on the how to show objects with no footprints.

    Attributes
    ----------
    shape : Optional[str], default="triangle"
        The shape of the object with no footprints.
    diameter_meters : Optional[float], default=10
        The diameter of the object with no footprints in meters.
    """

    shape: Optional[str] = "triangle"
    diameter_meters: Optional[float] = 10


class RiskModel(BaseModel):
    """The accepted input for the variable risk in Site.

    Attributes
    ----------
    return_periods : list[int]
        The return periods for the risk model.
    """

    return_periods: list = [1, 2, 5, 10, 25, 50, 100]


class DamageType(str, Enum):
    """The accepted input for the variable footprints_dmg_type."""

    absolute = "absolute"
    relative = "relative"
