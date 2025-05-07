from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from tomli import load as load_toml

from flood_adapt.config.fiat import DamageType
from flood_adapt.objects.forcing import unit_system as us


class Layer(BaseModel):
    """
    Base class for layers in the GUI.

    Attributes
    ----------
    bins : list[float]
        The bins for the layer.
    colors : list[str]
        The colors for the layer.
    """

    bins: list[float]
    colors: list[str]


class FloodMapLayer(Layer):
    zbmax: float
    depth_min: float


class AggregationDmgLayer(Layer):
    damage_decimals: Optional[int] = 0


class FootprintsDmgLayer(Layer):
    type: DamageType = DamageType.absolute
    damage_decimals: Optional[int] = 0
    buildings_min_zoom_level: int = 13


class BenefitsLayer(Layer):
    threshold: Optional[float] = None


class SviLayer(Layer):
    pass


class MapboxLayers(BaseModel):
    """The configuration of the mapbox layers in the gui.

    Attributes
    ----------
    floodmap : FloodMapLayer
        The configuration of the floodmap layer.
    aggregation_dmg : AggregationDmgLayer
        The configuration of the aggregation damage layer.
    footprints_dmg : FootprintsDmgLayer
        The configuration of the footprints damage layer.
    svi : SviLayer
        The configuration of the SVI layer.
    benefits : BenefitsLayer
        The configuration of the benefits layer.
    """

    floodmap: FloodMapLayer
    aggregation_dmg: AggregationDmgLayer
    footprints_dmg: FootprintsDmgLayer

    benefits: Optional[BenefitsLayer] = None
    svi: Optional[SviLayer] = None


class VisualizationLayers(Layer):
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
    mapbox_layers : MapboxLayers
        The configuration of the mapbox layers in the GUI.
    visualization_layers : VisualizationLayers
        The configuration of the visualization layers in the GUI.
    plotting : PlottingModel
        The configuration for creating hazard forcing plots.
    """

    units: GuiUnitModel
    mapbox_layers: MapboxLayers
    visualization_layers: VisualizationLayers
    plotting: PlottingModel

    @staticmethod
    def read_toml(path: Path) -> "GuiModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return GuiModel(**toml_contents)
