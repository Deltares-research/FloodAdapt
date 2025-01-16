from enum import Enum
from typing import Generic, Optional, Type, TypeVar

from pydantic import Field, field_validator, model_validator

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.io import unit_system as us


class MeasureCategory(str, Enum):
    """Class describing the accepted input for the variable 'type' in Measure."""

    impact = "impact"
    hazard = "hazard"


class MeasureType(str, Enum):
    # Hazard measures
    floodwall = "floodwall"
    thin_dam = "thin_dam"  # For now, same functionality as floodwall TODO: Add thin dam functionality
    levee = "levee"  # For now, same functionality as floodwall TODO: Add levee functionality
    pump = "pump"
    culvert = (
        "culvert"  # For now, same functionality as pump TODO: Add culvert functionality
    )
    water_square = "water_square"
    greening = "greening"
    total_storage = "total_storage"

    # Impact measures
    elevate_properties = "elevate_properties"
    buyout_properties = "buyout_properties"
    floodproof_properties = "floodproof_properties"

    @classmethod
    def is_hazard(cls, measure_type: str) -> bool:
        return measure_type in [
            cls.floodwall,
            cls.thin_dam,
            cls.levee,
            cls.pump,
            cls.culvert,
            cls.water_square,
            cls.greening,
            cls.total_storage,
        ]

    @classmethod
    def is_impact(cls, measure_type: str) -> bool:
        return measure_type in [
            cls.elevate_properties,
            cls.buyout_properties,
            cls.floodproof_properties,
        ]

    @classmethod
    def get_measure_category(cls, measure_type: str) -> MeasureCategory:
        if cls.is_hazard(measure_type):
            return MeasureCategory.hazard
        elif cls.is_impact(measure_type):
            return MeasureCategory.impact
        else:
            raise ValueError(f"Invalid measure type: {measure_type}")


class SelectionType(str, Enum):
    """Class describing the accepted input for the variable 'selection_type' in ImpactMeasure."""

    aggregation_area = "aggregation_area"
    polygon = "polygon"
    polyline = "polyline"
    all = "all"


class MeasureModel(IObjectModel):
    """BaseModel describing the expected variables and data types of attributes common to all measures."""

    type: MeasureType


class HazardMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures."""

    selection_type: SelectionType
    polygon_file: Optional[str] = Field(
        None,
        min_length=1,
        description="Path to a polygon file, either absolute or relative to the measure path.",
    )

    @field_validator("type")
    def validate_type(cls, value):
        if not MeasureType.is_hazard(value):
            raise ValueError(f"Invalid hazard type: {value}")
        return value

    @model_validator(mode="after")
    def validate_selection_type(self) -> "HazardMeasureModel":
        if (
            self.selection_type
            not in [SelectionType.aggregation_area, SelectionType.all]
            and self.polygon_file is None
        ):
            raise ValueError(
                "If `selection_type` is not 'aggregation_area' or 'all', then `polygon_file` needs to be set."
            )
        return self


class ImpactMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures."""

    type: MeasureType
    selection_type: SelectionType
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    polygon_file: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Path to a polygon file, relative to the database path.",
    )
    property_type: str  # TODO make enum

    @field_validator("type")
    def validate_type(cls, value):
        if not MeasureType.is_impact(value):
            raise ValueError(f"Invalid impact type: {value}")
        return value

    @model_validator(mode="after")
    def validate_aggregation_area_name(self):
        if (
            self.selection_type == SelectionType.aggregation_area
            and self.aggregation_area_name is None
        ):
            raise ValueError(
                "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set."
            )
        return self

    @model_validator(mode="after")
    def validate_polygon_file(self):
        if self.selection_type == SelectionType.polygon and self.polygon_file is None:
            raise ValueError(
                "If `selection_type` is 'polygon', then `polygon_file` needs to be set."
            )

        return self


class ElevateModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "elevate" impact measure."""

    elevation: us.UnitfulLengthRefValue


class BuyoutModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "buyout" impact measure."""

    ...  # Buyout has only the basic impact measure attributes


class FloodProofModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodproof" impact measure."""

    elevation: us.UnitfulLength


class FloodWallModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodwall" hazard measure."""

    elevation: us.UnitfulLength
    absolute_elevation: Optional[bool] = False


class PumpModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "pump" hazard measure."""

    discharge: us.UnitfulDischarge


class GreenInfrastructureModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "green infrastructure" hazard measure."""

    volume: us.UnitfulVolume
    height: Optional[us.UnitfulHeight] = None
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    percent_area: Optional[float] = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_hazard_type_values(self) -> "GreenInfrastructureModel":
        e_msg = f"Error parsing GreenInfrastructureModel: {self.name}"

        if self.type == MeasureType.total_storage:
            if self.height is not None or self.percent_area is not None:
                raise ValueError(
                    f"{e_msg}\nHeight and percent_area cannot be set for total storage type measures"
                )
            return self
        elif self.type == MeasureType.water_square:
            if self.percent_area is not None:
                raise ValueError(
                    f"{e_msg}\nPercentage_area cannot be set for water square type measures"
                )
            elif not isinstance(self.height, us.UnitfulHeight):
                raise ValueError(
                    f"{e_msg}\nHeight needs to be set for water square type measures"
                )
            return self
        elif self.type == MeasureType.greening:
            if not isinstance(self.height, us.UnitfulHeight) or not isinstance(
                self.percent_area, float
            ):
                raise ValueError(
                    f"{e_msg}\nHeight and percent_area needs to be set for greening type measures"
                )
        else:
            raise ValueError(
                f"{e_msg}\nType must be one of 'water_square', 'greening', or 'total_storage'"
            )
        return self

    @model_validator(mode="after")
    def validate_selection_type_values(self) -> "GreenInfrastructureModel":
        if self.selection_type == SelectionType.aggregation_area:
            if self.aggregation_area_name is None:
                raise ValueError(
                    "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set."
                )
            if self.aggregation_area_type is None:
                raise ValueError(
                    "If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set."
                )
        return self


T_MEASURE_MODEL = TypeVar("T_MEASURE_MODEL", bound=MeasureModel)


class IMeasure(IObject[T_MEASURE_MODEL], Generic[T_MEASURE_MODEL]):
    """A class for a FloodAdapt measure."""

    _attrs_type: Type[T_MEASURE_MODEL]

    dir_name = ObjectDir.measure
    display_name = "Measure"
