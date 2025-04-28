import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import pyproj
from pydantic import Field, field_validator, model_validator

from flood_adapt.config.site import Site
from flood_adapt.misc.utils import resolve_filepath, save_file_to_database
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.object_model import Object


class MeasureCategory(str, Enum):
    """Class describing the accepted input for the variable 'type' in Measure."""

    impact = "impact"
    hazard = "hazard"


class MeasureType(str, Enum):
    """Class describing the accepted input for the variable 'type' in Measure.

    Each type of measure is associated with a category (hazard or impact) and can be used to determine the type of measure.

    Attributes
    ----------
    floodwall : A floodwall measure.
    thin_dam : A thin dam measure.
    levee : A levee measure.
    pump : A pump measure.
    culvert : A culvert measure.
    water_square : A water square measure.
    greening : A greening measure.
    total_storage : A total storage measure.
    elevate_properties : An elevate properties measure.
    buyout_properties : A buyout properties measure.
    floodproof_properties : A floodproof properties measure.
    """

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
    """Class describing the accepted input for the variable 'selection_type' in Measures.

    It is used to determine where to apply the measure to a model.

    Attributes
    ----------
    aggregation_area : Use aggregation area as geometry for the measure.
    polygon : Use polygon as geometry for the measure.
    polyline : Use polyline as geometry for the measure.
    all : Apply the measure to all geometries in the database.
    """

    aggregation_area = "aggregation_area"
    polygon = "polygon"
    polyline = "polyline"
    all = "all"


class Measure(Object):
    """The expected variables and data types of attributes common to all measures.

    A measure is a collection of attributes that can be applied to a model.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type: MeasureType
        Type of measure. Should be one of the MeasureType enum values.
    """

    type: MeasureType


class HazardMeasure(Measure):
    """The expected variables and data types of attributes common to all hazard measures.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type: MeasureType
        Type of measure. Should be one of the MeasureType enum values and is_hazard.
    selection_type: SelectionType
        Type of selection. Should be one of the SelectionType enum values.
    polygon_file: str, Optional, default = None
        Path to a polygon file, either absolute or relative to the measure path in the database.

    """

    selection_type: SelectionType
    polygon_file: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Path to a polygon file, either absolute or relative to the measure path.",
    )

    @field_validator("type")
    def validate_type(cls, value):
        if not MeasureType.is_hazard(value):
            raise ValueError(f"Invalid hazard type: {value}")
        return value

    @model_validator(mode="after")
    def validate_selection_type(self) -> "HazardMeasure":
        if (
            self.selection_type
            not in [SelectionType.aggregation_area, SelectionType.all]
            and self.polygon_file is None
        ):
            raise ValueError(
                "If `selection_type` is not 'aggregation_area' or 'all', then `polygon_file` needs to be set."
            )
        return self

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.polygon_file:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            src_path = resolve_filepath("measures", self.name, self.polygon_file)
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.polygon_file = path.name


class ImpactMeasure(Measure):
    """The expected variables and data types of attributes common to all impact measures.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type: MeasureType
        Type of measure. Should be one of the MeasureType enum values and is_hazard.
    selection_type: SelectionType
        Type of selection. Should be one of the SelectionType enum values.
    polygon_file: str, Optional, default = None
        Path to a polygon file, either absolute or relative to the measure path in the database.
    property_type: str
        Type of property. Should be one of the PropertyType enum values.
    aggregation_area_type: str, Optional, default = None
        Type of aggregation area. Should be one of the SelectionType enum values.
    aggregation_area_name: str, Optional, default = None
            Name of the aggregation area.
    """

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

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save the additional files to the database."""
        if self.polygon_file:
            src_path = resolve_filepath("measures", self.name, self.polygon_file)
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.polygon_file = path.name


class Elevate(ImpactMeasure):
    """The expected variables and data types of the "elevate" impact measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type : MeasureType
        Type of measure. Should be "elevate_properties".
    selection_type : SelectionType
        Type of selection. Should be "polygon" or "aggregation_area".
    polygon_file : str, Optional
        Path to a polygon file, either absolute or relative to the measure path.
    aggregation_area_type : str, Optional
        Type of aggregation area. Should be "aggregation_area" or "all".
    aggregation_area_name : str, Optional
        Name of the aggregation area.
    property_type : str
        Type of property. Should be "residential" or "commercial".
    elevation : us.UnitfulLengthRefValue
        Elevation of the properties.
    """

    type: MeasureType = MeasureType.elevate_properties
    elevation: us.UnitfulLengthRefValue


class Buyout(ImpactMeasure):
    """The expected variables and data types of the "buyout" impact measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str, default ""
        Description of the measure.
    type : MeasureType, default MeasureType.buyout_properties
        Type of measure.
    selection_type : SelectionType
        Type of selection. Should be "polygon" or "aggregation_area".
    polygon_file : str, Optional
        Path to a polygon file, either absolute or relative to the measure path.
    aggregation_area_type : str, Optional
        Type of aggregation area. Should be "aggregation_area" or "all".
    aggregation_area_name : str, Optional
        Name of the aggregation area.
    property_type : str
        Type of property. Should be "residential" or "commercial".
    elevation : us.UnitfulLengthRefValue
        Elevation of the properties.

    """

    # Buyout has only the basic impact measure attributes
    type: MeasureType = MeasureType.buyout_properties


class FloodProof(ImpactMeasure):
    """The expected variables and data types of the "floodproof" impact measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type : MeasureType
        Type of measure. Should be "floodproof_properties".
    selection_type : SelectionType
        Type of selection. Should be "polygon" or "aggregation_area".
    polygon_file : str, Optional
        Path to a polygon file, either absolute or relative to the measure path.
    aggregation_area_type : str, Optional
        Type of aggregation area. Should be "aggregation_area" or "all".
    aggregation_area_name : str, Optional
        Name of the aggregation area.
    property_type : str
        Type of property. Should be "residential" or "commercial".
    elevation : us.UnitfulLengthRefValue
        Elevation of the properties.
    """

    type: MeasureType = MeasureType.floodproof_properties
    elevation: us.UnitfulLength


class FloodWall(HazardMeasure):
    """
    The expected variables and data types of the "floodwall" hazard measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type : MeasureType
        Type of measure. Should be "MeasureType.floodwall"
    selection_type : SelectionType
        Type of selection. Should be "SelectionType.polygon" or "SelectionType.aggregation_area".
    polygon_file : Optional[str]
        Path to a polygon file, either absolute or relative to the measure path.
    elevation : us.UnitfulLength
        Height of the floodwall.
    absolute_elevation : bool
        TODO remove?
    """

    type: MeasureType = MeasureType.floodwall
    elevation: us.UnitfulLength
    absolute_elevation: Optional[bool] = False


class Pump(HazardMeasure):
    """
    The expected variables and data types of the "pump" hazard measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type : MeasureType
        Type of measure. Should be "pump"
    selection_type : SelectionType
        Type of selection. Should be "polyline".
    polygon_file : str, Optional
        Path to a polygon file, either absolute or relative to the measure path.
    elevation : us.UnitfulLength
        Height of the floodwall.
    absolute_elevation : bool
        TODO remove?
    """

    type: MeasureType = MeasureType.pump
    discharge: us.UnitfulDischarge


class GreenInfrastructure(HazardMeasure):
    """The expected variables and data types of the "green infrastructure" hazard measure.

    Attributes
    ----------
    name: str
        Name of the measure.
    description: str
        Description of the measure.
    type : MeasureType
        Type of measure. Should be "greening"
    selection_type : SelectionType
        Type of selection. Should be "polygon" or "aggregation_area".
    height : us.UnitfulHeight, Optional
        Height of the green infrastructure.
    volume : us.UnitfulVolume, Optional
        Volume of the green infrastructure.
    polygon_file : str, Optional
        Path to a polygon file, either absolute or relative to the measure path.
    aggregation_area_type : str, Optional
        Type of aggregation area. Should be "aggregation_area".
    aggregation_area_name : str, Optional
        Name of the aggregation area.
    percent_area : float, Optional
        Percentage of the area that is green infrastructure.
    """

    type: MeasureType = MeasureType.greening
    volume: us.UnitfulVolume
    height: Optional[us.UnitfulHeight] = None
    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None
    percent_area: Optional[float] = Field(default=None, ge=0, le=100)

    @field_validator("height", mode="before", check_fields=False)
    def height_from_length(value: Any) -> Any:
        if isinstance(value, us.UnitfulLength):
            return us.UnitfulHeight(value=value.value, units=value.units)
        return value

    @model_validator(mode="after")
    def validate_hazard_type_values(self) -> "GreenInfrastructure":
        e_msg = f"Error parsing GreenInfrastructure: {self.name}"

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
    def validate_selection_type_values(self) -> "GreenInfrastructure":
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

    @staticmethod
    def calculate_volume(
        area: us.UnitfulArea,
        height: us.UnitfulHeight,
        percent_area: float = 100.0,
    ) -> float:
        """Determine volume from area of the polygon and infiltration height.

        Parameters
        ----------
        area : us.UnitfulArea
            Area of polygon with units (calculated using calculate_polygon_area)
        height : us.UnitfulHeight
            Water height with units
        percent_area : float, optional
            Percentage area covered by green infrastructure [%], by default 100.0

        Returns
        -------
        float
            Volume [m3]
        """
        volume = (
            area.convert(us.UnitTypesArea.m2)
            * height.convert(us.UnitTypesLength.meters)
            * (percent_area / 100.0)
        )
        return volume

    @staticmethod
    def calculate_polygon_area(gdf: gpd.GeoDataFrame, site: Site) -> float:
        """Calculate area of a GeoDataFrame Polygon.

        Parameters
        ----------
        gdf : gpd.GeoDataFrame
            Polygon object
        site : Site
            site config (used for CRS)

        Returns
        -------
        area : float
            Area of the given polygon
        """
        # Determine local CRS
        crs = pyproj.CRS.from_string(site.sfincs.config.csname)
        gdf = gdf.to_crs(crs)

        # The GeoJSON file can contain multiple polygons
        polygon = gdf.geometry
        # Calculate the area of all polygons
        area = polygon.area.sum()
        return area
