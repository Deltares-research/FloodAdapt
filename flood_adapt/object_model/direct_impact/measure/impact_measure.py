import os
from abc import ABC
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Union

import geopandas as gpd
from pydantic import validator

from flood_adapt.object_model.io.fiat import FiatModel
from flood_adapt.object_model.measure import MeasureModel
from flood_adapt.object_model.site import Site


class ImpactType(str, Enum):
    """Class describing the accepted input for the variable 'type' in ImpactMeasure"""

    elevate_properties = "elevate_properties"
    buyout = "buyout"
    floodproofing = "floodproofing"


class SelectionType(str, Enum):
    """Class describing the accepted input for the variable 'selection_type' in ImpactMeasure"""

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
    """ImpactMeasure class that holds all the information for a
    specific measure type that affects the impact model."""

    attrs: ImpactMeasureModel
    database_input_path: Union[str, os.PathLike]

    def get_object_ids(self) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        site = Site.load_file(
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        buildings = FiatModel(
            Path(self.database_input_path).parent / "static" / "templates" / "fiat"
        ).get_buildings(
            self.attrs.property_type,
            non_buildng_names=site.attrs.fiat.non_building_names,
        )

        if (self.attrs.selection_type == SelectionType.aggregation_area) or (
            self.attrs.selection_type == "all"
        ):
            if self.attrs.selection_type == "all":
                ids = buildings["Object ID"].to_numpy()
            elif self.attrs.selection_type == "aggregation_area":
                label = site.attrs.fiat.aggregation_shapefiles.split(".")[0]
                ids = buildings.loc[
                    buildings[f"Aggregation Label: {label}"]
                    == self.attrs.aggregation_area_name,
                    "Object ID",
                ].to_numpy()
        elif self.attrs.selection_type == "polygon":
            assert self.attrs.polygon_file is not None
            polygon = gpd.read_file(
                Path(self.database_input_path)
                / "measures"
                / self.attrs.name
                / self.attrs.polygon_file
            )
            ids = gpd.sjoin(buildings, polygon)["Object ID"].to_numpy()

        return list(ids)
