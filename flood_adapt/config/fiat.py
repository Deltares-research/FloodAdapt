from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from tomli import load as load_toml

from flood_adapt.config.sfincs import FloodmapType


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


class FiatConfigModel(BaseModel):
    """Configuration settings for the FIAT model.

    Attributes
    ----------
    exposure_crs : str
        The coordinate reference system of the exposure data.
    bfe : Optional[BFEModel], default=None
        The base flood elevation model.
    aggregation : list[AggregationModel]
        Configuration for the aggregation model.
    floodmap_type : FloodmapType
        The type of flood map to be used.
    non_building_names : Optional[list[str]], default=None
        List of non-building names to be used in the model.
    damage_unit : str, default="$"
        The unit of damage used in the model.
    building_footprints : Optional[str], default=None
        Path to the building footprints data.
    roads_file_name : Optional[str], default=None
        Path to the roads data.
    new_development_file_name : Optional[str], default="new_development_area.gpkg"
        Path to the new development area data.
    save_simulation : Optional[bool], default=False
        Whether to keep or delete the simulation files after the simulation is finished and all output files are created.
        If True, the simulation files are kept. If False, the simulation files are deleted.
    svi : Optional[SVIModel], default=None
        The social vulnerability index model.
    infographics : Optional[bool], default=False
        Whether to create infographics or not.
    no_footprints : Optional[NoFootprintsModel], default=NoFootprintsModel()
        Configuration for objects with no footprints.
    """

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
    """The expected variables and data types of attributes of the Fiat class.

    Attributes
    ----------
    risk : Optional[RiskModel]
        Configuration of probabilistic risk runs. default=None
    config : FiatConfigModel
        Configuration for the FIAT model.
    benefits : Optional[BenefitsModel]
        Configuration for running benefit calculations. default=None
    """

    config: FiatConfigModel

    benefits: Optional[BenefitsModel] = None
    risk: Optional[RiskModel] = None

    @staticmethod
    def read_toml(path: Path) -> "FiatModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return FiatModel(**toml_contents)
