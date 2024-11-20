from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import Field, model_validator, validator

from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
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


T = TypeVar("T")


class MeasureModel(IObjectModel, Generic[T]):
    """BaseModel describing the expected variables and data types of attributes common to all measures."""

    type: T

    @model_validator(mode="after")
    def validate_type(self) -> "MeasureModel":
        if not isinstance(self.type, (ImpactType, HazardType)):
            raise ValueError(
                f"Type must be one of {ImpactType.__members__} or {HazardType.__members__}"
            )
        return self


class HazardMeasureModel(MeasureModel[HazardType]):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures."""

    type: HazardType
    selection_type: SelectionType
    polygon_file: Optional[str] = Field(
        None,
        min_length=1,
        description="Path to a polygon file, either absolute or relative to the measure path.",
    )

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


class ImpactMeasureModel(MeasureModel[ImpactType]):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures."""

    type: ImpactType
    selection_type: SelectionType
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    polygon_file: Optional[str] = Field(
        None,
        min_length=1,
        description="Path to a polygon file, relative to the database path.",
    )
    property_type: str  # TODO make enum

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
        e_msg = f"Error parsing GreenInfrastructureModel: {self.name}"

        if self.type == HazardType.total_storage:
            if self.height is not None or self.percent_area is not None:
                raise ValueError(
                    f"{e_msg}\nHeight and percent_area cannot be set for total storage type measures"
                )
            return self
        elif self.type == HazardType.water_square:
            if self.percent_area is not None:
                raise ValueError(
                    f"{e_msg}\nPercentage_area cannot be set for water square type measures"
                )
            elif not isinstance(self.height, UnitfulHeight):
                raise ValueError(
                    f"{e_msg}\nHeight needs to be set for water square type measures"
                )
            return self
        elif self.type == HazardType.greening:
            if not isinstance(self.height, UnitfulHeight) or not isinstance(
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


MeasureModelType = TypeVar("MeasureModelType", bound=MeasureModel)


class IMeasure(IObject[MeasureModelType]):
    """A class for a FloodAdapt measure."""

    dir_name = ObjectDir.measure
    display_name = "Measure"

    attrs: MeasureModelType


HazardMeasureModelType = TypeVar("HazardMeasureModelType", bound=HazardMeasureModel)


class HazardMeasure(IMeasure[HazardMeasureModel], Generic[HazardMeasureModelType]):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model."""

    attrs: HazardMeasureModel


ImpactMeasureModelType = TypeVar("ImpactMeasureModelType", bound=ImpactMeasureModel)


class ImpactMeasure(IMeasure[ImpactMeasureModel], Generic[ImpactMeasureModelType]):
    """All the information for a specific measure type that affects the impact model."""

    attrs: ImpactMeasureModel
