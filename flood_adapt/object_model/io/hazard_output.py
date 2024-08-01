from enum import Enum

from pydantic import BaseModel


class TemporalOutputType(str, Enum):
    csv = "csv"


class SpatialOutputType(str, Enum):
    netcdf = "netcdf"
    shapefile = "shapefile"
    geotiff = "geotiff"
    geopackage = "geopackage"
    geojson = "geojson"


class HazardData(BaseModel):
    path: str
    _type: TemporalOutputType | SpatialOutputType

    # TODO write conversion functions for each type
