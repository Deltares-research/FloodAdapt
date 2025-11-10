import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import tomli
from pydantic import BaseModel, Field, model_validator

from flood_adapt.config.impacts import DamageType
from flood_adapt.objects import unit_system as us


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
    decimals: Optional[int] = 0

    @model_validator(mode="after")
    def check_bins_and_colors(self) -> "Layer":
        """Check that the bins and colors have the same length."""
        if (len(self.bins) + 1) != len(self.colors):
            raise ValueError(
                f"Number of bins ({len(self.bins)}) must be one less than number of colors ({len(self.colors)})"
            )
        return self


class FloodMapLayer(Layer):
    zbmax: float
    depth_min: float
    roads_min_zoom_level: int = 14


class FootprintsDmgLayer(Layer):
    type: DamageType = DamageType.absolute


class BenefitsLayer(Layer):
    threshold: Optional[float] = None


class LogicalOperator(str, Enum):
    AND = "and"
    OR = "or"


class FieldName(str, Enum):
    """Enum for valid field names with mapping to dictionary keys."""

    NAME = "name"
    LONG_NAME = "long_name"
    DESCRIPTION = "description"

    @property
    def dict_key(self) -> str:
        """Get the actual dictionary key for this field name."""
        mapping = {
            "name": "name",
            "long_name": "Long Name",
            "description": "Description",
        }
        return mapping[self.value]


class FilterCondition(BaseModel):
    """A single filter condition."""

    field_name: FieldName
    values: list[Any]
    operator: LogicalOperator = (
        LogicalOperator.OR
    )  # How to combine values within this condition


class FilterGroup(BaseModel):
    """A group of filter conditions with logical operators."""

    conditions: list[FilterCondition]
    operator: LogicalOperator = (
        LogicalOperator.OR
    )  # How to combine conditions within this group


class MetricLayer(Layer):
    type: str
    # Simplified: just a single FilterGroup or FilterCondition
    filters: Union[FilterGroup, FilterCondition] = Field(
        default_factory=lambda: FilterGroup(conditions=[])
    )

    def matches(self, data_dict: dict) -> bool:
        """Check if the given data dictionary matches the filter criteria."""
        if isinstance(self.filters, FilterCondition):
            return self._evaluate_condition(self.filters, data_dict)
        else:  # FilterGroup
            return self._evaluate_filter_group(self.filters, data_dict)

    def _evaluate_filter_group(self, group: FilterGroup, data_dict: dict) -> bool:
        """Evaluate a single filter group."""
        if not group.conditions:
            return True

        condition_results = []
        for condition in group.conditions:
            condition_results.append(self._evaluate_condition(condition, data_dict))

        if group.operator == LogicalOperator.AND:
            return all(condition_results)
        else:  # OR
            return any(condition_results)

    def _evaluate_condition(self, condition: FilterCondition, data_dict: dict) -> bool:
        """Evaluate a single condition."""
        # Use the dict_key property to get the actual dictionary key
        field_value = data_dict.get(condition.field_name.dict_key)
        if field_value is None:
            return False

        value_matches = [value in field_value for value in condition.values]  # noqa: PD011

        if condition.operator == LogicalOperator.AND:
            return all(value_matches)
        else:  # OR
            return any(value_matches)


class AggregationDmgLayer(MetricLayer):
    type: str = "damage"
    filters: FilterGroup = Field(
        default_factory=lambda: FilterGroup(
            conditions=[
                FilterCondition(
                    field_name=FieldName.NAME,
                    values=[
                        "TotalDamageEvent",
                        "ExpectedAnnualDamages",
                        "TotalDamageRP",
                        "EWEAD",
                    ],
                )
            ]
        )
    )


class OutputLayers(BaseModel):
    """The configuration of the mapbox layers in the gui.

    Attributes
    ----------
    floodmap : FloodMapLayer
        The configuration of the floodmap layer.
    aggregation_dmg : AggregationDmgLayer
        The configuration of the aggregation damage layer.
    footprints_dmg : FootprintsDmgLayer
        The configuration of the footprints damage layer.

    benefits : BenefitsLayer
        The configuration of the benefits layer.
    """

    floodmap: FloodMapLayer
    aggregation_dmg: AggregationDmgLayer
    footprints_dmg: FootprintsDmgLayer
    aggregated_metrics: list[MetricLayer] = Field(default_factory=list)
    benefits: Optional[BenefitsLayer] = None

    def get_aggr_metrics_layers(
        self,
        metrics: list[dict],
        type: Literal["single_event", "risk"] = "single_event",
        rp: Optional[int] = None,
        equity: bool = False,
    ):
        layer_types = [self.aggregation_dmg] + self.aggregated_metrics
        filtered_input_metrics = self._filter_metrics(metrics, type, rp, equity)
        return self._match_metrics_to_layers(filtered_input_metrics, layer_types)

    def _should_skip_metric(
        self, metric_name: str, rp: Optional[int], equity: bool
    ) -> bool:
        rp_match = re.search(r"RP(\d+)", metric_name)
        y_match = re.search(r"(\d+)Y", metric_name)
        name_match = rp_match or y_match

        if rp is None:
            if name_match:
                return True
            if not equity and "EW" in metric_name:
                return True
            if equity and "EW" not in metric_name:
                return True
        return False

    def _process_metric_name(
        self, metric_name: str, rp: Optional[int]
    ) -> tuple[str, bool]:
        rp_match = re.search(r"RP(\d+)", metric_name)
        y_match = re.search(r"(\d+)Y", metric_name)
        name_match = rp_match or y_match
        if rp is not None:
            if name_match:
                extracted_rp = int(name_match.group(1))
                name_check = extracted_rp == int(rp)
                cleaned_name = re.sub(r"(RP\d+|\d+Y)", "", metric_name)
                return cleaned_name.rstrip("_"), name_check
            else:
                return metric_name, False
        return metric_name, True

    def _filter_metrics(self, metrics, type, rp, equity):
        filtered = []
        for metric in metrics:
            metric_name = metric.get("name", "")
            metric["name_to_show"] = metric_name
            if type == "risk":
                if self._should_skip_metric(metric_name, rp, equity):
                    continue
                metric["name_to_show"], name_check = self._process_metric_name(
                    metric_name, rp
                )
                if rp is not None and not name_check:
                    continue
            filtered.append(metric)
        return filtered

    def _match_metrics_to_layers(self, metrics, layer_types):
        filtered_metrics = []
        for metric in metrics:
            for layer in layer_types:
                if layer.matches(metric):
                    filtered_metrics.append(
                        {
                            "metric": metric,
                            "bins": getattr(layer, "bins", None),
                            "colors": getattr(layer, "colors", None),
                            "decimals": getattr(layer, "decimals", None),
                        }
                    )
                    break
        return filtered_metrics


class VisualizationLayer(Layer):
    """The configuration of a layer to visualize in the gui.

    name : str
        The name of the layer to visualize.
    long_name : str
        The long name of the layer to visualize.
    path : str
        The path to the layer data to visualize.
    field_name : str
        The field names of the layer to visualize.
    decimals : Optional[int]
        The number of decimals to use for the layer to visualize. default is None.
    """

    name: str
    long_name: str
    path: str
    field_name: str
    decimals: Optional[int] = None


_DEFAULT_BIN_NR = 4


def interpolate_hex_colors(
    start_hex="#FFFFFF", end_hex="#860000", number_bins=_DEFAULT_BIN_NR
):
    """
    Interpolate between two hex colors and returns a list of number_bins hex color codes.

    Parameters
    ----------
        start_hex : str
            Starting color in hex format (e.g., "#FFFFFF").
        end_hex : str
            Ending color in hex format (e.g., "#000000").
        number_bins : int
            Number of colors to generate between the start and end colors.

    Returns
    -------
        list[str]
            List of hex color codes interpolated between the start and end colors.
    """

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb_color):
        return "#{:02X}{:02X}{:02X}".format(*rgb_color)

    start_rgb = hex_to_rgb(start_hex)
    end_rgb = hex_to_rgb(end_hex)

    interpolated_colors = []
    for i in range(number_bins):
        ratio = i / (number_bins - 1) if number_bins > 1 else 0
        interpolated_rgb = tuple(
            int(start + (end - start) * ratio) for start, end in zip(start_rgb, end_rgb)
        )
        interpolated_colors.append(rgb_to_hex(interpolated_rgb))

    return interpolated_colors


class VisualizationLayers(BaseModel):
    """The configuration of the layers you might want to visualize in the gui.

    Attributes
    ----------
    default : Layer
        The default layer settings the visualization layers.
    layers : list[VisualizationLayer]
        The layers to visualize.
    """

    buildings_min_zoom_level: int = 13
    layers: list[VisualizationLayer] = Field(default_factory=list)

    def add_layer(
        self,
        name: str,
        long_name: str,
        path: str,
        field_name: str,
        database_path: Path,
        decimals: Optional[int] = None,
        bins: Optional[list[float]] = None,
        colors: Optional[list[str]] = None,
    ) -> None:
        if not Path(path).is_absolute():
            raise ValueError(f"Path {path} must be absolute.")

        data = gpd.read_file(path)
        if field_name not in data.columns:
            raise ValueError(
                f"Field name {field_name} not found in data. Available fields: {data.columns.tolist()}"
            )

        if bins is None:
            _, _bins = pd.qcut(
                data[field_name], _DEFAULT_BIN_NR, retbins=True, duplicates="drop"
            )
            bins = _bins.tolist()[1:-1]

        if decimals is None:
            non_zero_bins = [abs(b) for b in bins if b != 0]
            min_non_zero = min(non_zero_bins) if non_zero_bins else 1
            decimals = max(int(-np.floor(np.log10(min_non_zero))), 0)

        if colors is None:
            nr_bins = len(bins) + 1
            colors = interpolate_hex_colors(number_bins=nr_bins)

        relative_path = Path(path).relative_to(database_path / "static")
        self.layers.append(
            VisualizationLayer(
                bins=bins,
                colors=colors,
                name=name,
                long_name=long_name,
                path=relative_path.as_posix(),
                field_name=field_name,
                decimals=decimals,
            )
        )


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
    output_layers : OutputLayers
        The configuration of the mapbox layers in the GUI.
    visualization_layers : VisualizationLayers
        The configuration of the visualization layers in the GUI.
    plotting : PlottingModel
        The configuration for creating hazard forcing plots.
    """

    units: GuiUnitModel
    output_layers: OutputLayers
    visualization_layers: VisualizationLayers
    plotting: PlottingModel

    @staticmethod
    def read_toml(path: Path) -> "GuiModel":
        with open(path, mode="rb") as fp:
            toml_contents = tomli.load(fp)

        return GuiModel(**toml_contents)
