from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from tomli import load as load_toml

from flood_adapt.config.fiat import DamageType
from flood_adapt.objects.forcing import unit_system as us


class MapboxLayersModel(BaseModel):
    """The configuration of the mapbox layers in the gui.

    Attributes
    ----------
    buildings_min_zoom_level : int
        The minimum zoom level for the buildings layer.
    flood_map_depth_min : float
        The minimum depth for the flood map layer.
    flood_map_zbmax : float
        The maximum depth for the flood map layer.
    flood_map_bins : list[float]
        The bins for the flood map layer.
    flood_map_colors : list[str]
        The colors for the flood map layer.
    aggregation_dmg_bins : list[float]
        The bins for the aggregation damage layer.
    aggregation_dmg_colors : list[str]
        The colors for the aggregation damage layer.
    footprints_dmg_type : DamageType
        The type of damage for the footprints layer.
    footprints_dmg_bins : list[float]
        The bins for the footprints layer.
    footprints_dmg_colors : list[str]
        The colors for the footprints layer.
    svi_bins : Optional[list[float]]
        The bins for the SVI layer.
    svi_colors : Optional[list[str]]
        The colors for the SVI layer.
    benefits_bins : list[float]
        The bins for the benefits layer.
    benefits_colors : list[str]
        The colors for the benefits layer.
    benefits_threshold : Optional[float], default=None
        The threshold for the benefits layer.
    damage_decimals : Optional[int], default=0
        The number of decimals for the damage layer.

    """

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
    """The configuration of the layers you might want to visualize in the gui.

    Attributes
    ----------
    default_bin_number : int
        The default number of bins for the visualization layers.
    default_colors : list[str]
        The default colors for the visualization layers.
    layer_names : list[str]
        The names of the layers to visualize.
    layer_long_names : list[str]
        The long names of the layers to visualize.
    layer_paths : list[str]
        The paths to the layers to visualize.
    field_names : list[str]
        The field names of the layers to visualize.
    bins : Optional[list[list[float]]]
        The bins for the layers to visualize.
    colors : Optional[list[list[str]]]
        The colors for the layers to visualize.
    """

    # TODO add check for default_bin_number and default_colors to have the same length
    default_bin_number: int
    default_colors: list[str]
    layer_names: list[str] = Field(default_factory=list)
    layer_long_names: list[str] = Field(default_factory=list)
    layer_paths: list[str] = Field(default_factory=list)
    field_names: list[str] = Field(default_factory=list)
    bins: Optional[list[list[float]]] = Field(default_factory=list)
    colors: Optional[list[list[str]]] = Field(default_factory=list)


class GuiUnitModel(BaseModel):
    """The unit system used in the GUI.

    Attributes
    ----------
    default_length_units : us.UnitTypesLength
        The length units used in the GUI.
    default_distance_units : us.UnitTypesLength
        The distance units used in the GUI.
    default_area_units : us.UnitTypesArea
        The area units used in the GUI.
    default_volume_units : us.UnitTypesVolume
        The volume units used in the GUI.
    default_velocity_units : us.UnitTypesVelocity
        The velocity units used in the GUI.
    default_direction_units : us.UnitTypesDirection
        The direction units used in the GUI.
    default_discharge_units : us.UnitTypesDischarge
        The discharge units used in the GUI.
    default_intensity_units : us.UnitTypesIntensity
        The intensity units used in the GUI.
    default_cumulative_units : us.UnitTypesLength
        The cumulative units used in the GUI.
    """

    default_length_units: us.UnitTypesLength
    default_distance_units: us.UnitTypesLength
    default_area_units: us.UnitTypesArea
    default_volume_units: us.UnitTypesVolume
    default_velocity_units: us.UnitTypesVelocity
    default_direction_units: us.UnitTypesDirection
    default_discharge_units: us.UnitTypesDischarge
    default_intensity_units: us.UnitTypesIntensity
    default_cumulative_units: us.UnitTypesLength

    @staticmethod
    def imperial() -> "GuiUnitModel":
        return GuiUnitModel(
            default_length_units=us.UnitTypesLength.feet,
            default_distance_units=us.UnitTypesLength.miles,
            default_area_units=us.UnitTypesArea.sf,
            default_volume_units=us.UnitTypesVolume.cf,
            default_velocity_units=us.UnitTypesVelocity.mph,
            default_direction_units=us.UnitTypesDirection.degrees,
            default_discharge_units=us.UnitTypesDischarge.cfs,
            default_intensity_units=us.UnitTypesIntensity.inch_hr,
            default_cumulative_units=us.UnitTypesLength.inch,
        )

    @staticmethod
    def metric() -> "GuiUnitModel":
        return GuiUnitModel(
            default_length_units=us.UnitTypesLength.meters,
            default_distance_units=us.UnitTypesLength.meters,
            default_area_units=us.UnitTypesArea.m2,
            default_volume_units=us.UnitTypesVolume.m3,
            default_velocity_units=us.UnitTypesVelocity.mps,
            default_direction_units=us.UnitTypesDirection.degrees,
            default_discharge_units=us.UnitTypesDischarge.cms,
            default_intensity_units=us.UnitTypesIntensity.mm_hr,
            default_cumulative_units=us.UnitTypesLength.millimeters,
        )


class SyntheticTideModel(BaseModel):
    """Configuration for the synthetic tide.

    Parameters
    ----------
    harmonic_amplitude : us.UnitfulLength
        The amplitude of the tide harmonic relative to the datum.
    datum : str
        The datum to which the harmonic amplitude is relative.
        Should be a datum defined in `site.sfincs.waterlevels.datums`
    """

    harmonic_amplitude: us.UnitfulLength
    datum: str


class PlottingModel(BaseModel):
    """
    The configuration of the plotting in the gui.

    Attributes
    ----------
    excluded_datums : list[str]
        A list of datums that will be excluded from the forcing plot in event windows.
    synthetic_tide : SyntheticTideModel
        The configuration of the synthetic tide.
    """

    synthetic_tide: SyntheticTideModel
    excluded_datums: list[str] = Field(default_factory=list)


class GuiModel(BaseModel):
    """The accepted input for the variable gui in Site.

    Attributes
    ----------
    units : GuiUnitModel
        The unit system used in the GUI.
    mapbox_layers : MapboxLayersModel
        The configuration of the mapbox layers in the GUI.
    visualization_layers : VisualizationLayersModel
        The configuration of the visualization layers in the GUI.
    plotting : PlottingModel
        The configuration for creating hazard forcing plots.
    """

    units: GuiUnitModel
    mapbox_layers: MapboxLayersModel
    visualization_layers: VisualizationLayersModel
    plotting: PlottingModel

    @staticmethod
    def read_toml(path: Path) -> "GuiModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return GuiModel(**toml_contents)
