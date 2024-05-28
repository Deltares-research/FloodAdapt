import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator, validator

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulDischarge,
    UnitfulHeight,
    UnitfulLength,
    UnitfulLengthRefValue,
    UnitfulVolume,
)


class ImpactType(str, Enum):
    """Class describing the accepted input for the variable 'type' in ImpactMeasure."""

    elevate_properties = "elevate_properties"
    buyout_properties = "buyout_properties"
    floodproof_properties = "floodproof_properties"


class HazardType(str, Enum):
    """Class describing the accepted input for the variable 'type' in HazardMeasure."""

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


class SelectionType(str, Enum):
    """Class describing the accepted input for the variable 'selection_type' in ImpactMeasure."""

    aggregation_area = "aggregation_area"
    polygon = "polygon"
    polyline = "polyline"
    all = "all"


class MeasureModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to all measures."""

    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    type: Union[HazardType, ImpactType]


class HazardMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures."""

    type: HazardType
    selection_type: SelectionType
    polygon_file: Optional[str] = None

    @field_validator("polygon_file")
    @classmethod
    def validate_polygon_file(cls, v: Optional[str]) -> Optional[str]:
        if len(v) == 0:
            raise ValueError("Polygon file path cannot be empty")
        return v

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

    type: ImpactType
    selection_type: SelectionType
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    polygon_file: Optional[str] = None
    property_type: str

    # TODO #94 pydantic validators do not currently work

    @validator("aggregation_area_name")
    def validate_aggregation_area_name(
        cls, aggregation_area_name: Optional[str], values: Any
    ) -> Optional[str]:
        if (
            values.get("selection_type") == SelectionType.aggregation_area
            and aggregation_area_name is None
        ):
            raise ValueError(
                "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set."
            )
        return aggregation_area_name

    @validator("polygon_file")
    def validate_polygon_file(
        cls, polygon_file: Optional[str], values: Any
    ) -> Optional[str]:
        if (
            values.get("selection_type") == SelectionType.polygon
            and polygon_file is None
        ):
            raise ValueError(
                "If `selection_type` is 'polygon', then `polygon_file` needs to be set."
            )
        return polygon_file


class ElevateModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "elevate" impact measure."""

    elevation: UnitfulLengthRefValue


class BuyoutModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "buyout" impact measure."""

    ...  # Buyout has only the basic impact measure attributes


class FloodProofModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodproof" impact measure."""

    elevation: UnitfulLength


class FloodWallModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodwall" hazard measure."""

    elevation: UnitfulLength
    absolute_elevation: Optional[bool] = False


class PumpModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "pump" hazard measure."""

    discharge: UnitfulDischarge


class GreenInfrastructureModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "green infrastructure" hazard measure."""

    volume: UnitfulVolume
    height: Optional[UnitfulHeight] = None
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    percent_area: Optional[float] = Field(None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_hazard_type_values(self) -> "GreenInfrastructureModel":
        if self.type == HazardType.total_storage:
            if self.height is not None or self.percent_area is not None:
                raise ValueError(
                    "Height and percent_area cannot be set for total storage type measures"
                )
            return self
        elif self.type == HazardType.water_square:
            if self.percent_area is not None:
                raise ValueError(
                    "Percentage_area cannot be set for water square type measures"
                )
            elif not isinstance(self.height, UnitfulHeight):
                raise ValueError(
                    "Height needs to be set for water square type measures"
                )
            return self
        elif self.type == HazardType.greening:
            if not isinstance(self.height, UnitfulHeight) or not isinstance(
                self.percent_area, float
            ):
                raise ValueError(
                    "Height and percent_area needs to be set for greening type measures"
                )
        else:
            raise ValueError(
                "Type must be one of 'water_square', 'greening', or 'total_storage'"
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


class IMeasure(ABC):
    """A class for a FloodAdapt measure."""

    attrs: MeasureModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Get Measure attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """Get Measure attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Measure attributes to a toml file."""


class IElevate(IMeasure):
    """A class for a FloodAdapt "elevate" measure."""

    attrs: ElevateModel


class IBuyout(IMeasure):
    """A class for a FloodAdapt "buyout" measure."""

    attrs: BuyoutModel


class IFloodProof(IMeasure):
    """A class for a FloodAdapt "floodproof" measure."""

    attrs: FloodProofModel


class IFloodWall(IMeasure):
    """A class for a FloodAdapt "floodwall" measure."""

    attrs: FloodWallModel


class IPump(IMeasure):
    """A class for a FloodAdapt "pump" measure."""

    attrs: PumpModel


class IGreenInfrastructure(IMeasure):
    """A class for a FloodAdapt "green infrastrcutre" measure."""

    attrs: GreenInfrastructureModel
