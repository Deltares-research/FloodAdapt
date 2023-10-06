import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulLength,
    UnitTypesArea,
    UnitTypesDirection,
    UnitTypesDischarge,
    UnitTypesIntensity,
    UnitTypesLength,
    UnitTypesVelocity,
    UnitTypesVolume,
)


class Cstype(str, Enum):
    """class describing the accepted input for the variable cstype in Site"""

    projected = "projected"
    spherical = "spherical"


class Floodmap_type(str, Enum):
    """class describing the accepted input for the variable floodmap in Site"""

    water_level = "water_level"
    water_depth = "water_depth"


class SfincsModel(BaseModel):
    """class describing the accepted input for the variable sfincs in Site"""

    csname: str
    cstype: Cstype
    version: Optional[str] = ""
    offshore_model: str
    overland_model: str
    ambient_air_pressure: float
    floodmap_units: UnitTypesLength
    save_simulation: bool


class VerticalReferenceModel(BaseModel):
    name: str
    height: UnitfulLength


class WaterLevelReferenceModel(BaseModel):
    reference: VerticalReferenceModel
    localdatum: VerticalReferenceModel
    msl: VerticalReferenceModel
    other: Optional[list[VerticalReferenceModel]]  # only for plotting


class Cyclone_track_databaseModel(BaseModel):
    """class describing the accepted input for the variable cyclone_track_database in Site"""

    file: str


class SlrModel(BaseModel):
    """class describing the accepted input for the variable slr in Site"""

    vertical_offset: UnitfulLength
    relative_to_year: int

class MapboxLayersModel(BaseModel):
    flood_map_bins: list[float]
    flood_map_colors: list[str]
    aggregation_dmg_bins: list[float]
    aggregation_dmg_colors: list[str]
    footprints_dmg_bins: list[float]
    footprints_dmg_colors: list[str]
    svi_bins: Optional[list[float]]
    svi_colors: Optional[list[str]]  
    damage_decimals: Optional[int] = 0

class GuiModel(BaseModel):
    """class describing the accepted input for the variable gui in Site"""

    tide_harmonic_amplitude: UnitfulLength
    default_length_units: UnitTypesLength
    default_distance_units: UnitTypesLength
    default_area_units: UnitTypesArea
    default_volume_units: UnitTypesVolume
    default_velocity_units: UnitTypesVelocity
    default_direction_units: UnitTypesDirection
    default_discharge_units: UnitTypesDischarge
    default_intensity_units: UnitTypesIntensity
    default_cumulative_units: UnitTypesLength
    mapbox_layers: MapboxLayersModel


class RiskModel(BaseModel):
    """class describing the accepted input for the variable risk in Site"""

    flooding_threshold: UnitfulLength
    return_periods: list


class DemModel(BaseModel):
    """class describing the accepted input for the variable dem in Site"""

    filename: str
    units: UnitTypesLength


class EquityModel(BaseModel):
    census_data: str
    # aggregation_type: str
    # aggregation_label: Optional[str] = "name"
    percapitalincome_label: Optional[str] = "PerCapitalIncome"
    totalpopulation_label: Optional[str] = "TotalPopulation"


class AggregationModel(BaseModel):
    name: str
    file: str
    field_name: str
    equity: Optional[EquityModel]


class BFEModel(BaseModel):
    geom: str
    table: Optional[str]
    field_name: str


class SVIModel(BaseModel):
    geom: str
    field_name: str


class FiatModel(BaseModel):
    """class describing the accepted input for the variable fiat in Site"""

    exposure_crs: str
    bfe: BFEModel
    aggregation: list[AggregationModel]
    floodmap_type: Floodmap_type
    non_building_names: Optional[list[str]]
    damage_unit: Optional[str] = "$"
    building_footprints: Optional[str]
    roads_file_name: Optional[str]
    new_development_file_name: Optional[str]
    save_simulation: Optional[bool] = False
    svi: Optional[SVIModel]


class RiverModel(BaseModel):
    """class describing the accepted input for the variable river in Site"""

    name: str
    description: str
    mean_discharge: UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class Obs_stationModel(BaseModel):
    """class describing the accepted input for the variable obs_station in Site"""

    name: Union[int, str]
    description: Optional[str] = ""
    ID: int
    lat: float
    lon: float
    mllw: Optional[UnitfulLength]
    mhhw: Optional[UnitfulLength]
    localdatum: Optional[UnitfulLength]
    msl: Optional[UnitfulLength]


class BenefitsModel(BaseModel):
    current_year: int
    current_projection: str
    baseline_strategy: str
    event_set: str


class SCSModel(BaseModel):
    """class describing the accepted input for the variable scs, which included the file with
    the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type
    """

    file: str
    type: str


class StandardObjectModel(BaseModel):
    """class describing the accepted input for the variable standard_object in Site"""

    events: Optional[list[str]] = []
    projections: Optional[list[str]] = []
    strategies: Optional[list[str]] = []


class SiteModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes of the Site class"""

    name: str
    description: Optional[str] = ""
    lat: float
    lon: float
    sfincs: SfincsModel
    water_level: WaterLevelReferenceModel
    cyclone_track_database: Cyclone_track_databaseModel
    slr: SlrModel
    gui: GuiModel
    risk: RiskModel
    dem: DemModel
    fiat: FiatModel
    river: Optional[list[RiverModel]]
    obs_station: Optional[Obs_stationModel]
    benefits: BenefitsModel
    scs: Optional[SCSModel]  # optional for the US to use SCS rainfall curves
    standard_objects: Optional[
        StandardObjectModel
    ] = StandardObjectModel()  # optional for the US to use standard objects


class ISite(ABC):
    attrs: SiteModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Site attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """get Site attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Site attributes to a toml file"""
