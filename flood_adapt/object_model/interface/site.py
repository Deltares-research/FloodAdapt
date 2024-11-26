import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, model_validator
from pydantic.functional_validators import AfterValidator
from typing_extensions import Annotated

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


def ensure_ascii(s: str):
    assert s.isascii()
    return s


AsciiStr = Annotated[str, AfterValidator(ensure_ascii)]


class Cstype(str, Enum):
    """The accepted input for the variable cstype in Site."""

    projected = "projected"
    spherical = "spherical"


class FloodmapType(str, Enum):
    """The accepted input for the variable floodmap in Site."""

    water_level = "water_level"
    water_depth = "water_depth"


class TideGaugeSource(str, Enum):
    """The accepted input for the variable source in tide_gauge."""

    file = "file"
    noaa_coops = "noaa_coops"


class SfincsModel(BaseModel):
    """The accepted input for the variable sfincs in Site."""

    csname: AsciiStr
    cstype: Cstype
    version: Optional[AsciiStr] = ""
    offshore_model: Optional[AsciiStr] = None
    overland_model: AsciiStr
    floodmap_units: UnitTypesLength
    save_simulation: Optional[bool] = False


class VerticalReferenceModel(BaseModel):
    """The accepted input for the variable vertical_reference in Site."""

    name: AsciiStr
    height: UnitfulLength


class WaterLevelReferenceModel(BaseModel):
    """The accepted input for the variable water_level in Site."""

    localdatum: VerticalReferenceModel
    msl: VerticalReferenceModel
    other: Optional[list[VerticalReferenceModel]] = Field(
        default_factory=list
    )  # only for plotting


class CycloneTrackDatabaseModel(BaseModel):
    """The accepted input for the variable cyclone_track_database in Site."""

    file: AsciiStr


class SlrScenariosModel(BaseModel):
    """The accepted input for the variable slr.scenarios ."""

    file: AsciiStr
    relative_to_year: int


class SlrModel(BaseModel):
    """The accepted input for the variable slr in Site."""

    vertical_offset: UnitfulLength
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
    footprints_dmg_type: DamageType = DamageType.absolute
    footprints_dmg_bins: list[float]
    footprints_dmg_colors: list[str]
    svi_bins: Optional[list[float]] = Field(default_factory=list)
    svi_colors: Optional[list[str]] = Field(default_factory=list)
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
    bins: Optional[list[list[float]]] = Field(default_factory=list)
    colors: Optional[list[list[str]]] = Field(default_factory=list)


class GuiModel(BaseModel):
    """The accepted input for the variable gui in Site."""

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
    visualization_layers: VisualizationLayersModel


class RiskModel(BaseModel):
    """The accepted input for the variable risk in Site."""

    return_periods: list


class FloodFrequencyModel(BaseModel):
    """The accepted input for the variable flood_frequency in Site."""

    flooding_threshold: UnitfulLength


class DemModel(BaseModel):
    """The accepted input for the variable dem in Site."""

    filename: AsciiStr
    units: UnitTypesLength


class EquityModel(BaseModel):
    census_data: AsciiStr
    percapitaincome_label: Optional[str] = "PerCapitaIncome"
    totalpopulation_label: Optional[str] = "TotalPopulation"


class AggregationModel(BaseModel):
    name: AsciiStr
    file: AsciiStr
    field_name: AsciiStr
    equity: Optional[EquityModel] = None


class BFEModel(BaseModel):
    geom: AsciiStr
    table: Optional[AsciiStr] = None
    field_name: AsciiStr


class SVIModel(BaseModel):
    geom: AsciiStr
    field_name: AsciiStr


class FiatModel(BaseModel):
    """The accepted input for the variable fiat in Site."""

    exposure_crs: str
    bfe: Optional[BFEModel] = None
    aggregation: list[AggregationModel]
    floodmap_type: FloodmapType
    non_building_names: Optional[list[str]] = None
    damage_unit: str = "$"
    building_footprints: Optional[str] = None
    roads_file_name: Optional[str] = None
    new_development_file_name: Optional[str] = None
    save_simulation: Optional[bool] = False
    svi: Optional[SVIModel] = None
    infographics: Optional[bool] = False


class RiverModel(BaseModel):
    """Model that describes the accepted input for the variable river in Site."""

    name: AsciiStr
    description: AsciiStr
    mean_discharge: UnitfulDischarge
    x_coordinate: float
    y_coordinate: float


class TideGaugeModel(BaseModel):
    """The accepted input for the variable tide_gauge in Site.

    The obs_station is used for the download of tide gauge data, to be added to the hazard model as water level boundary condition.
    """

    name: Optional[Union[int, AsciiStr]] = None
    description: Optional[AsciiStr] = None
    source: TideGaugeSource
    ID: Optional[int] = None  # This is the only attribute that is currently used in FA!
    file: Optional[AsciiStr] = None  # for locally stored data
    lat: Optional[float] = None
    lon: Optional[float] = None

    @model_validator(mode="after")
    def validate_selection_type(self) -> "TideGaugeModel":
        if self.source == "file" and self.file is None:
            raise ValueError(
                "If `source` is 'file' a file path relative to the static folder should be provided with the attribute 'file'."
            )
        elif self.source == "noaa_coops" and self.ID is None:
            raise ValueError(
                "If `source` is 'noaa_coops' the id of the station should be provided with the attribute 'ID'."
            )

        return self


class ObsPointModel(BaseModel):
    """The accepted input for the variable obs_point in Site.

    obs_points is used to define output locations in the hazard model, which will be plotted in the user interface.
    """

    name: Union[int, AsciiStr]
    description: Optional[AsciiStr] = ""
    ID: Optional[int] = (
        None  # if the observation station is also a tide gauge, this ID should be the same as for obs_station
    )
    file: Optional[AsciiStr] = None  # for locally stored data
    lat: float
    lon: float


class BenefitsModel(BaseModel):
    current_year: int
    current_projection: AsciiStr
    baseline_strategy: AsciiStr
    event_set: AsciiStr


class SCSModel(BaseModel):
    """Class describing the accepted input for the variable scs.

    Includes the file with the non-dimensional SCS rainfall curves in the site folder and the SCS rainfall curve type.

    """

    file: AsciiStr
    type: AsciiStr


class StandardObjectModel(BaseModel):
    """The accepted input for the variable standard_object in Site."""

    events: Optional[list[AsciiStr]] = Field(default_factory=list)
    projections: Optional[list[AsciiStr]] = Field(default_factory=list)
    strategies: Optional[list[AsciiStr]] = Field(default_factory=list)


class SiteModel(BaseModel):
    """The expected variables and data types of attributes of the Site class."""

    name: AsciiStr
    description: Optional[AsciiStr] = ""
    lat: float
    lon: float
    sfincs: SfincsModel
    water_level: WaterLevelReferenceModel
    cyclone_track_database: Optional[CycloneTrackDatabaseModel] = None
    slr: SlrModel
    gui: GuiModel
    risk: RiskModel
    flood_frequency: FloodFrequencyModel = FloodFrequencyModel(
        flooding_threshold=UnitfulLength(value=0.0, units=UnitTypesLength.meters)
    )
    dem: DemModel
    fiat: FiatModel
    tide_gauge: Optional[TideGaugeModel] = None
    river: Optional[list[RiverModel]] = None
    obs_point: Optional[list[ObsPointModel]] = None
    benefits: BenefitsModel
    scs: Optional[SCSModel] = None  # optional for the US to use SCS rainfall curves

    standard_objects: Optional[StandardObjectModel] = (
        StandardObjectModel()
    )  # optional for the US to use standard objects


class ISite(ABC):
    _attrs: SiteModel

    @property
    @abstractmethod
    def attrs(self) -> SiteModel:
        """Get the site attributes as a dictionary.

        Returns
        -------
        SiteModel
            Pydantic model with the site attributes
        """
        ...

    @attrs.setter
    @abstractmethod
    def attrs(self, value: SiteModel):
        """Set the site attributes from a dictionary.

        Parameters
        ----------
        value : SiteModel
            Pydantic model with the site attributes
        """
        ...

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Site attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any]):
        """Get Site attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Site attributes to a toml file."""
        ...
