import os
import warnings
from enum import Enum
from pathlib import Path
from typing import Any, Optional, TypeVar

import geopandas as gpd
import pyproj
from pydantic import (
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from flood_adapt.config.site import Site
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.objects.forcing import unit_system as us
from flood_adapt.objects.object_model import Object

logger = FloodAdaptLogging.getLogger(__name__)


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


T = TypeVar("T", bound="Measure")


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
    selection_type: SelectionType
        Type of selection. Should be one of the SelectionType enum values.
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
    aggregation_area_name: str, Optional
        Name of the aggregation area. Required if `selection_type` is 'aggregation_area'.
    aggregation_area_type: str, Optional
        Type of aggregation area. Required if `selection_type` is 'aggregation_area'.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: MeasureType
    selection_type: SelectionType
    gdf: Optional[gpd.GeoDataFrame | str | Path] = Field(
        default=None,
        description="GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.",
    )
    polygon_file: Optional[str] = Field(
        default=None,
        description="[DEPRECATED] Use `gdf` instead.",
        exclude=True,  # don't serialize back out
    )

    aggregation_area_type: Optional[str] = None
    aggregation_area_name: Optional[str] = None

    @model_validator(mode="after")
    def validate_selection_type(self) -> "Measure":
        match self.selection_type:
            case SelectionType.all:
                pass
            case SelectionType.polygon | SelectionType.polyline:
                if self.gdf is None:
                    raise ValueError(
                        "If `selection_type` is 'polygon' or 'polyline', then `gdf` needs to be set."
                    )
            case SelectionType.aggregation_area:
                if self.aggregation_area_name is None:
                    raise ValueError(
                        "If `selection_type` is 'aggregation_area', then `aggregation_area_name` needs to be set."
                    )
                if self.aggregation_area_type is None:
                    raise ValueError(
                        "If `selection_type` is 'aggregation_area', then `aggregation_area_type` needs to be set."
                    )
            case _:
                raise ValueError(
                    f"Invalid selection type: {self.selection_type}. "
                    "Must be one of 'aggregation_area', 'polygon', 'polyline', or 'all'."
                )
        return self

    @model_validator(mode="before")
    def migrate_polygon_file(cls, values):
        """Migrate deprecated `polygon_file` to `gdf` automatically."""
        if (
            "polygon_file" in values
            and values.get("polygon_file")
            and not values.get("gdf")
        ):
            polygon_file = values.pop("polygon_file")
            warnings.warn(
                "`polygon_file` is deprecated and will be removed in a future release. "
                "Use `gdf` instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            values["gdf"] = polygon_file
        return values

    @field_serializer("gdf")
    def serialize_gdf(self, gdf: gpd.GeoDataFrame | str | Path) -> str:
        if isinstance(gdf, gpd.GeoDataFrame):
            return f"{self.name}.geojson"
        elif isinstance(gdf, Path):
            return gdf.with_suffix(".geojson").as_posix()
        return Path(gdf).with_suffix(".geojson").as_posix()

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.gdf is not None:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            if isinstance(self.gdf, gpd.GeoDataFrame):
                self.gdf.to_crs(epsg=4326).to_file(
                    Path(output_dir) / f"{self.name}.geojson"
                )
            elif isinstance(self.gdf, Path):
                dst = Path(output_dir, self.gdf.name).with_suffix(".geojson")
                gpd.read_file(self.gdf).to_file(dst)
            else:
                dst = Path(output_dir, Path(self.gdf).name).with_suffix(".geojson")
                gpd.read_file(self.gdf).to_file(dst)

    def read(self, directory: Path) -> None:
        if self.gdf is not None and isinstance(self.gdf, (str, Path)):
            gdf = gpd.read_file(directory / self.gdf)
            if gdf.crs is not None:
                gdf = gdf.to_crs(epsg=4326)
            else:
                logger.warning(f"No CRS defined in {self.gdf}, assuming EPSG:4326")
                gdf = gdf.set_crs(epsg=4326)
            self.gdf = gdf

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            # don't attempt to compare against unrelated types
            return False

        _self = self.model_dump(
            exclude={"name", "description", "gdf"}, exclude_none=True
        )
        _other = value.model_dump(
            exclude={"name", "description", "gdf"}, exclude_none=True
        )
        if _self != _other:
            # different non-gdf attributes
            return False

        # different gdf attribute
        if self.gdf is not None and value.gdf is None:
            return False
        elif value.gdf is not None and self.gdf is None:
            return False

        # Both not None, compare GeoDataFrames
        if self.gdf is not None:
            if isinstance(self.gdf, gpd.GeoDataFrame):
                _self_gdf = self.gdf
            elif isinstance(self.gdf, (str, Path)):
                _self_gdf = gpd.read_file(self.gdf).to_crs(epsg=4326)
            else:
                return False

            if isinstance(value.gdf, gpd.GeoDataFrame):
                _other_gdf = value.gdf
            elif isinstance(value.gdf, (str, Path)):
                _other_gdf = gpd.read_file(value.gdf).to_crs(epsg=4326)
            else:
                return False

            if not _self_gdf.equals(_other_gdf):
                return False

        # All attributes equal
        return True


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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.

    """

    @field_validator("type")
    def validate_type(cls, value):
        if not MeasureType.is_hazard(value):
            raise ValueError(f"Invalid hazard type: {value}")
        return value


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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
    property_type: str
        Type of property. Should be one of the PropertyType enum values.
    aggregation_area_type: str, Optional, default = None
        Type of aggregation area. Should be one of the SelectionType enum values.
    aggregation_area_name: str, Optional, default = None
            Name of the aggregation area.
    """

    property_type: str  # TODO make enum

    @field_validator("type")
    def validate_type(cls, value):
        if not MeasureType.is_impact(value):
            raise ValueError(f"Invalid impact type: {value}")
        return value


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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
    polygon_file: str, Optional, DEPRECATED
        [DEPRECATED] Use `gdf` instead.
    gdf: gpd.GeoDataFrame | str | Path, Optional
        GeoDataFrame representation of the polygon file. If a string or Path is provided, it is treated as a file path to load the GeoDataFrame from.
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
