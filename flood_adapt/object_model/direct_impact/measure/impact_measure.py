from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
from pydantic import validator

from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.io.fiat_data import FiatModel
from flood_adapt.object_model.measure import MeasureModel


class ImpactType(str, Enum):
    """class describing the accepted input for the variable 'type' in ImpactMeasure"""

    elevate_properties = "elevate_properties"
    buyout = "buyout"
    floodproofing = "floodproofing"


class SelectionType(str, Enum):
    """class describing the accepted input for the variable 'selection_type' in ImpactMeasure"""

    aggregation_area = "aggregation_area"
    polygon = "polygon"
    all = "all"


class ImpactMeasureModel(MeasureModel):
    """BaseModel describing the expected variables and data types of attributes common to all impact measures"""

    type: ImpactType
    selection_type: SelectionType
    aggregation_area_name: Optional[str]
    polygon_file: Optional[str]
    property_type: str

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


class ImpactMeasure(ABC):
    """ImpactMeasure class that holds all the information for a specific measure type that affects the impact model"""

    attrs: ImpactMeasureModel

    def get_object_ids(self) -> list[Any]:
        """Get ids of objects that are affected by the measure"""
        database = (
            DatabaseIO()
        )  # TODO this should should be updated by the new dbs_controller class
        buildings = FiatModel(database.database_path).get_buildings(
            self.attrs.property_type
        )

        if (self.attrs.selection_type == SelectionType.aggregation_area) or (
            self.attrs.selection_type == "all"
        ):
            if self.attrs.selection_type == "all":
                ids = buildings["Object ID"].to_numpy()
            elif self.attrs.selection_type == "aggregation_area":
                ids = buildings.loc[
                    buildings["Aggregation Label: subdivision"]
                    == self.attrs.aggregation_area_name,
                    "Object ID",
                ].to_numpy()  # TODO: aggregation label should be read from site config
        elif self.attrs.selection_type == "polygon":
            assert self.attrs.polygon_file is not None
            polygon = gpd.read_file(
                Path(database.measures_path) / self.attrs.name / self.attrs.polygon_file
            )
            ids = gpd.sjoin(buildings, polygon)["Object ID"].to_numpy()

        return list(ids)
