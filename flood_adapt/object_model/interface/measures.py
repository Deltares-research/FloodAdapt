import os
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, validator

from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulLengthRefValue,
)


class ImpactType(str, Enum):
    """Class describing the accepted input for the variable 'type' in ImpactMeasure"""

    elevate_properties = "elevate_properties"
    buyout_properties = "buyout_properties"
    floodproof_properties = "floodproof_properties"


class HazardType(str, Enum):
    """Class describing the accepted input for the variable 'type' in HazardMeasure"""

    floodwall = "floodwall"
    pump = "pump"


class SelectionType(str, Enum):
    """Class describing the accepted input for the variable 'selection_type' in ImpactMeasure"""

    aggregation_area = "aggregation_area"
    polygon = "polygon"
    all = "all"


class MeasureModel(BaseModel):
    """BaseModel describing the expected variables and data types of attributes common to all measures"""

    name: str
    long_name: str
    type: str


class HazardMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures"""

    type: HazardType
    polygon_file: str


class ImpactMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures"""

    type: ImpactType
    selection_type: SelectionType
    aggregation_area_type: Optional[str]
    aggregation_area_name: Optional[str]
    polygon_file: Optional[str]
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
    """BaseModel describing the expected variables and data types of the "elevate" impact measure"""

    elevation: UnitfulLengthRefValue


class BuyoutModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "buyout" impact measure"""

    ...  # Buyout has only the basic impact measure attributes


class FloodProofModel(ImpactMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodproof" impact measure"""

    elevation: UnitfulLength


class FloodWallModel(HazardMeasureModel):
    """BaseModel describing the expected variables and data types of the "floodwall" hazard measure"""

    elevation: UnitfulLength


class IMeasure(ABC):
    """This is a class for a FloodAdapt measure"""

    attrs: MeasureModel

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """get Measure attributes from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """get Measure attributes from an object, e.g. when initialized from GUI"""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """save Measure attributes to a toml file"""


class IElevate(IMeasure):
    """This is a class for a FloodAdapt "elevate" measure"""

    attrs: ElevateModel


class IBuyout(IMeasure):
    """This is a class for a FloodAdapt "buyout" measure"""

    attrs: BuyoutModel


class IFloodProof(IMeasure):
    """This is a class for a FloodAdapt "floodproof" measure"""

    attrs: FloodProofModel


class IFloodWall(IMeasure):
    """This is a class for a FloodAdapt "floodwall" measure"""

    attrs: FloodWallModel
