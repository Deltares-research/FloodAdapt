from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from tomli import load as load_toml

from flood_adapt.object_model.interface.config.sfincs import FloodmapType


class BenefitsModel(BaseModel):
    current_year: int
    current_projection: str
    baseline_strategy: str
    event_set: str


class EquityModel(BaseModel):
    census_data: str
    percapitaincome_label: Optional[str] = "PerCapitaIncome"
    totalpopulation_label: Optional[str] = "TotalPopulation"


class AggregationModel(BaseModel):
    name: str
    file: str
    field_name: str
    equity: Optional[EquityModel] = None


class BFEModel(BaseModel):
    geom: str
    table: Optional[str] = None
    field_name: str


class SVIModel(BaseModel):
    geom: str
    field_name: str


class NoFootprintsModel(BaseModel):
    """
    The configuration on the how to show objects with no footprints.

    Attributes
    ----------
        shape (Optional[str]): The shape of the object. Default is "triangle".
        diameter_meters (Optional[float]): The diameter of the object in meters. Default is 10.
    """

    shape: Optional[str] = "triangle"
    diameter_meters: Optional[float] = 10


class RiskModel(BaseModel):
    """The accepted input for the variable risk in Site."""

    return_periods: list = [1, 2, 5, 10, 25, 50, 100]


class DamageType(str, Enum):
    """The accepted input for the variable footprints_dmg_type."""

    absolute = "absolute"
    relative = "relative"


class FiatConfigModel(BaseModel):
    """The accepted input for the variable fiat in Site."""

    exposure_crs: str
    bfe: Optional[BFEModel] = None
    aggregation: list[AggregationModel]
    floodmap_type: FloodmapType
    non_building_names: Optional[list[str]]
    damage_unit: str = "$"
    building_footprints: Optional[str] = None
    roads_file_name: Optional[str] = None
    new_development_file_name: Optional[str] = "new_development_area.gpkg"
    save_simulation: Optional[bool] = False
    svi: Optional[SVIModel] = None
    infographics: Optional[bool] = False
    no_footprints: Optional[NoFootprintsModel] = NoFootprintsModel()

    @staticmethod
    def read_toml(path: Path) -> "FiatConfigModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return FiatConfigModel(**toml_contents)


class FiatModel(BaseModel):
    risk: RiskModel

    config: FiatConfigModel
    benefits: BenefitsModel

    @staticmethod
    def read_toml(path: Path) -> "FiatModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return FiatModel(**toml_contents)
