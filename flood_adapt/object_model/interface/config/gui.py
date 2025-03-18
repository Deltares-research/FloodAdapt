from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field
from tomli import load as load_toml

from flood_adapt.object_model.interface.config.fiat import DamageType
from flood_adapt.object_model.io import unit_system as us


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
    default_length_units: us.UnitTypesLength
    default_distance_units: us.UnitTypesLength
    default_area_units: us.UnitTypesArea
    default_volume_units: us.UnitTypesVolume
    default_velocity_units: us.UnitTypesVelocity
    default_direction_units: us.UnitTypesDirection
    default_discharge_units: us.UnitTypesDischarge
    default_intensity_units: us.UnitTypesIntensity
    default_cumulative_units: us.UnitTypesLength


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

    Parameters
    ----------
    excluded_datums : list[str]
        A list of datums that will be excluded from the forcing plot in event windows.
    synthetic_tide : SyntheticTideModel
        The configuration of the synthetic tide.
    """

    synthetic_tide: SyntheticTideModel
    excluded_datums: list[str] = Field(default_factory=list)


class GuiModel(BaseModel):
    """The accepted input for the variable gui in Site."""

    units: GuiUnitModel
    mapbox_layers: MapboxLayersModel
    visualization_layers: VisualizationLayersModel
    plotting: PlottingModel

    @staticmethod
    def read_toml(path: Path) -> "GuiModel":
        with open(path, mode="rb") as fp:
            toml_contents = load_toml(fp)

        return GuiModel(**toml_contents)
