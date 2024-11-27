from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel

from flood_adapt.object_model.hazard.interface.tide_gauge import TideGaugeModel
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import ObjectDir
from flood_adapt.object_model.io import unit_system as us


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"


class Floodmap_type(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class SfincsModel(BaseModel):
    """The accepted input for the variable sfincs in Site."""

    csname: str
    cstype: Cstype
    version: Optional[str] = ""
    offshore_model: Optional[str] = None
    overland_model: str
    floodmap_units: us.UnitTypesLength
    save_simulation: Optional[bool] = False


class VerticalReferenceModel(BaseModel):
    """The accepted input for the variable vertical_reference in Site."""

    name: str
    height: us.UnitfulLength


class WaterLevelReferenceModel(BaseModel):
    """The accepted input for the variable water_level in Site."""

    localdatum: VerticalReferenceModel
    msl: VerticalReferenceModel
    other: Optional[list[VerticalReferenceModel]] = []  # only for plotting


class Cyclone_track_databaseModel(BaseModel):
    """The accepted input for the variable cyclone_track_database in Site."""

    file: str


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr.scenarios ."""

    file: str
    relative_to_year: int


class SlrModel(BaseModel):
    """The accepted input for the variable slr in Site."""

    vertical_offset: us.UnitfulLength
    scenarios: Optional[SlrScenariosModel] = None


class DamageType(str, Enum):
    """The accepted input for the variable footprints_dmg_type."""

    absolute = "absolute"
    relative = "relative"


class MapboxLayersModel(BaseModel):
    """The configuration of the mapbox layers in the gui."""

    buildings_min_zoom_level: int = 13
    flood_map_depth_min: float
    flood_map_zbmax: float
    flood_map_bins: list[float]
    flood_map_colors: list[str]
    aggregation_dmg_bins: list[float]
    aggregation_dmg_colors: list[str]
    footprints_dmg_type: DamageType = "absolute"
    footprints_dmg_bins: list[float]
    footprints_dmg_colors: list[str]
    svi_bins: Optional[list[float]] = []
    svi_colors: Optional[list[str]] = []
    benefits_bins: list[float]
    benefits_colors: list[str]
    benefits_threshold: Optional[float] = None
    damage_decimals: Optional[int] = 0


class VisualizationLayersModel(BaseModel):
    """The configuration of the layers you might want to visualize in the gui."""

    default_bin_number: int
    default_colors: list[str]
    layer_names: list[str]
    layer_long_names: list[str]
    layer_paths: list[str]
    field_names: list[str]
    bins: Optional[list[list[float]]] = []
    colors: Optional[list[list[str]]] = []


class GuiModel(BaseModel):
    """The accepted input for the variable gui in Site."""

    tide_harmonic_amplitude: us.UnitfulLength
    default_length_units: us.UnitTypesLength
    default_distance_units: us.UnitTypesLength
    default_area_units: us.UnitTypesArea
    default_volume_units: us.UnitTypesVolume
    default_velocity_units: us.UnitTypesVelocity
    default_direction_units: us.UnitTypesDirection
    default_discharge_units: us.UnitTypesDischarge
    default_intensity_units: us.UnitTypesIntensity
    default_cumulative_units: us.UnitTypesLength
    mapbox_layers: MapboxLayersModel
    visualization_layers: VisualizationLayersModel


class RiskModel(BaseModel):
    """The accepted input for the variable risk in Site."""

    return_periods: list


class FloodFrequencyModel(BaseModel):
    """The accepted input for the variable flood_frequency in Site."""

    flooding_threshold: us.UnitfulLength


class DemModel(BaseModel):
    """The accepted input for the variable dem in Site."""

    filename: str
    units: us.UnitTypesLength


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


class FiatModel(BaseModel):
    """The accepted input for the variable fiat in Site."""

    exposure_crs: str
    bfe: Optional[BFEModel] = None
    aggregation: list[AggregationModel]
    floodmap_type: Floodmap_type
    non_building_names: Optional[list[str]]
    damage_unit: Optional[str] = "$"
    building_footprints: Optional[str] = None
    roads_file_name: Optional[str] = None
    new_development_file_name: Optional[str] = None
    save_simulation: Optional[bool] = False
    svi: Optional[SVIModel] = None
    infographics: Optional[bool] = False


class RiverModel(BaseModel):
    """Model that describes the accepted input for the variable river in Site."""

    name: str
    description: Optional[str] = None
    mean_discharge: us.UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class Obs_pointModel(BaseModel):
    """The accepted input for the variable obs_point in Site.

    obs_points is used to define output locations in the hazard model, which will be plotted in the user interface.
    """

    name: Union[int, str]
    description: Optional[str] = ""
    ID: Optional[int] = (
        None  # if the observation station is also a tide gauge, this ID should be the same as for obs_station
    )
    file: Optional[str] = None  # for locally stored data
    lat: float
    lon: float


class BenefitsModel(BaseModel):
    current_year: int
    current_projection: str
    baseline_strategy: str
    event_set: str


class SCSModel(BaseModel):
    """Class describing the accepted input for the variable scs.

    Includes the file with the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type.

    """

    file: str
    type: str


class StandardObjectModel(BaseModel):
    """The accepted input for the variable standard_object in Site."""

    events: Optional[list[str]] = []
    projections: Optional[list[str]] = []
    strategies: Optional[list[str]] = []


class SiteModel(IObjectModel):
    """The expected variables and data types of attributes of the Site class."""

    lat: float
    lon: float
    crs: str = "EPSG:4326"
    sfincs: SfincsModel
    water_level: WaterLevelReferenceModel
    cyclone_track_database: Optional[Cyclone_track_databaseModel] = None
    slr: SlrModel
    gui: GuiModel
    risk: RiskModel
    # TODO what should the default be
    flood_frequency: Optional[FloodFrequencyModel] = FloodFrequencyModel(
        flooding_threshold=us.UnitfulLength(value=0.0, units=us.UnitTypesLength.meters)
    )
    dem: DemModel
    fiat: FiatModel
    tide_gauge: Optional[TideGaugeModel] = None
    river: Optional[list[RiverModel]] = None
    obs_point: Optional[list[Obs_pointModel]] = None
    benefits: BenefitsModel
    scs: Optional[SCSModel] = None  # optional for the US to use SCS rainfall curves

    standard_objects: Optional[StandardObjectModel] = (
        StandardObjectModel()
    )  # optional for the US to use standard objects


class Site(IObject[SiteModel]):
    _attrs_type = SiteModel
    dir_name = ObjectDir.site
    display_name = "Site"
