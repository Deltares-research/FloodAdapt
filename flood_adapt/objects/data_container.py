from __future__ import annotations

import logging
from abc import abstractmethod
from pathlib import Path
from typing import Any, ClassVar, Generic, TypeVar

import geopandas as gpd
import pandas as pd
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_serializer,
    model_validator,
)
from shapely.affinity import translate

from flood_adapt.objects import unit_system as us

__all__ = [
    "DataContainer",
    "GeoDataFrameContainer",
    "NetCDFContainer",
    "DataFrameContainer",
]


logger = logging.getLogger(__name__)

# The type of the underlying data object (e.g., GeoDataFrame, Dataset, DataFrame)
T = TypeVar("T")


class DataContainer(BaseModel, Generic[T]):
    """Generic reference to external or lazily-loaded data.

    Designed as a base class for data types like GeoDataFrames, NetCDF datasets, CSVs, etc.

    Attributes
    ----------
    name: str
        Name of the data reference. If not provided, defaults to the path's filename, or "Unnamed DataContainer".
    path : Path | str | None
        Absolute or relative path to the data file.
    _data : T | None
        The actual loaded data object.
    _read : bool
        Flag controlling whether to automatically load the data after validation.
    """

    name: str = Field(
        default="Unnamed DataContainer", description="Name of the data reference."
    )
    path: Path | str | None = Field(default=None, description="Path to the data file.")

    _data: T | None = PrivateAttr(default=None)
    _read: bool = PrivateAttr(default=False)
    _extension: ClassVar[str] = ""

    # --- Validation and initialization ---

    @field_validator("path", mode="before")
    def _convert_str_to_path(cls, value: Path | str | None) -> Path | None:
        if isinstance(value, str):
            return Path(value)
        return value

    @model_validator(mode="after")
    def _overwrite_default_name_from_path(self) -> "DataContainer":
        if (
            self.name == DataContainer.model_fields["name"].default
            and self.path is not None
        ):
            self.name = Path(self.path).stem
        return self

    # --- Abstract methods ---
    @abstractmethod
    def read(self, directory: Path | None = None) -> None:
        """Read the data from `path` into `_data`.

        Subclasses must implement this method.
        """
        ...

    @abstractmethod
    def write(self, directory: Path | None = None) -> None:
        """Write `_data` to the given directory or its original path.

        Subclasses must implement this method.
        """
        ...

    @abstractmethod
    def _compare_data(self, data_a: T, data_b: T) -> bool:
        """Override for type-specific equality behavior.

        Subclasses must implement this method.
        """
        ...

    # --- Common functionality ---
    @property
    def data(self) -> T:
        """Access the underlying data object, loading it if necessary."""
        if self._data is None:
            self.read()
        return self._data

    @property
    def _filename(self) -> str:
        """Get the filename with extension for this data container."""
        ext = (
            self._extension
            if self._extension.startswith(".")
            else f".{self._extension}"
        )
        return f"{self.name}{ext}"

    def set_data(self, data: T) -> None:
        """Set the in-memory data object manually."""
        self._data = data

    def has_data(self) -> bool:
        """Check if data is currently loaded in memory."""
        return self._data is not None

    def resolved_path(self, directory: Path | None = None) -> Path:
        """Return an absolute resolved path, optionally relative to a given directory."""
        if self.path is not None:
            self.path = Path(self.path)
            if self.path.is_absolute():
                path = self.path
            elif directory is not None:
                path = directory / self.path
            else:
                raise ValueError(
                    "Cannot resolve relative path without a base directory."
                )
        elif directory is not None:
            path = directory / self._filename
        elif self.path is None and directory is None:
            path = Path(self._filename)
        else:
            raise ValueError("Cannot resolve path without a base directory.")
        return path

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        # This loads data if not already loaded
        if not self._compare_data(self.data, other.data):
            return False

        return True

    # --- Serialization ---
    @model_serializer()
    def serialize_model(self) -> dict[str, Any]:
        """Serialize DataContainer into a simple JSON-safe dict."""
        # assume _data is always set, so we write the data to disk separately, and only store the path here
        return {"path": self._filename}


class GeoDataFrameContainer(DataContainer[gpd.GeoDataFrame]):
    """Reference to a GeoDataFrame on disk."""

    _extension: ClassVar[str] = ".geojson"

    def read(self, directory: Path | None = None) -> None:
        path = self.resolved_path(directory)
        if not path.exists():
            raise FileNotFoundError(f"GeoDataFrame file not found: {path}")
        gdf = gpd.read_file(path)
        if gdf.crs is None:
            logger.warning(f"No CRS defined in {path}, assuming EPSG:4326")
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)
        self._data = gdf

    def write(self, directory: Path | None = None) -> None:
        if self.data is None:
            raise ValueError("No data loaded to write.")

        path = self.resolved_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.data.to_file(path)

    def _compare_data(self, data_a: gpd.GeoDataFrame, data_b: gpd.GeoDataFrame) -> bool:
        return data_a.equals(data_b)


class NetCDFContainer(DataContainer[xr.Dataset]):
    """Reference to a NetCDF dataset on disk."""

    _extension: ClassVar[str] = ".nc"

    def read(self, directory: Path | None = None) -> None:
        path = self.resolved_path(directory)
        if not path.exists():
            raise FileNotFoundError(f"NetCDF file not found: {path}")
        self._data = xr.load_dataset(path)

    def write(self, directory: Path | None = None) -> None:
        if self._data is None:
            raise ValueError("No data loaded to write.")
        path = self.resolved_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._data.to_netcdf(path)

    def _compare_data(self, data_a: xr.Dataset, data_b: xr.Dataset) -> bool:
        return data_a.equals(data_b)


class DataFrameContainer(DataContainer[pd.DataFrame]):
    """Reference to a pandas DataFrame stored on disk (CSV, Parquet, etc.)."""

    _extension: ClassVar[str] = ".csv"

    def read(
        self, directory: Path | None = None, open_kwargs: dict | None = None
    ) -> None:
        path = self.resolved_path(directory)
        if not path.exists():
            raise FileNotFoundError(f"DataFrame file not found: {path}")
        open_kwargs = open_kwargs or {}

        # Determine file format from extension
        suffix = path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(path, **open_kwargs)
        elif suffix in (".parquet", ".pq"):
            df = pd.read_parquet(path, **open_kwargs)
        elif suffix in (".feather", ".ftr"):
            df = pd.read_feather(path, **open_kwargs)
        else:
            raise ValueError(f"Unsupported DataFrame format: {suffix}")

        self._data = df

    def write(self, directory: Path | None = None) -> None:
        if self._data is None:
            raise ValueError("No data loaded to write.")

        path = self.resolved_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)

        suffix = path.suffix.lower()
        if suffix == ".csv":
            self._data.to_csv(path, index=False)
        elif suffix in (".parquet", ".pq"):
            self._data.to_parquet(path)
        elif suffix in (".feather", ".ftr"):
            self._data.to_feather(path)
        else:
            raise ValueError(f"Unsupported DataFrame format for writing: {suffix}")

    def _compare_data(self, data_a: pd.DataFrame, data_b: pd.DataFrame) -> bool:
        return data_a.equals(data_b)


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    northsouth_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )


class CycloneTrackContainer(DataContainer[TropicalCyclone]):
    _extension: ClassVar[str] = ".cyc"

    def read(self, directory: Path | None = None) -> None:
        path = self.resolved_path(directory)
        if not path.exists():
            raise FileNotFoundError(f"Cyclone track file not found: {path}")

        self._data = TropicalCyclone()
        self._data.read_track(path, fmt="ddb_cyc")

    def write(self, directory: Path | None = None) -> None:
        if self.data is None:
            raise ValueError("No data loaded to write.")

        path = self.resolved_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)

        self._data.write_track(path, fmt="ddb_cyc")

    def to_spw(
        self,
        directory: Path | None = None,
        include_rainfall: bool = True,
        recreate: bool = True,
    ) -> Path:
        if self.data is None:
            raise ValueError("No data loaded to write.")

        path = self.resolved_path(directory)
        path.parent.mkdir(parents=True, exist_ok=True)
        path = path.with_suffix(".spw")
        self._data.include_rainfall = include_rainfall
        if not path.exists():
            self._data.to_spiderweb(filename=path)
        elif recreate:
            path.unlink()
            self._data.to_spiderweb(filename=path)
        return path

    def translate_track(self, translation: TranslationModel) -> None:
        if self.data is None:
            raise ValueError("Cannot translate undefined track")

        if (
            translation.eastwest_translation == 0
            and translation.northsouth_translation == 0
        ):
            return

        logger.info(f"Translating the track of the tropical cyclone `{self.name}`")
        cyclone = self._data.track.to_crs(epsg=4326)

        # Translate the track in the local coordinate system
        cyclone["geometry"] = cyclone["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=translation.eastwest_translation.convert(
                    us.UnitTypesLength.meters
                ),
                yoff=translation.northsouth_translation.convert(
                    us.UnitTypesLength.meters
                ),
            )
        )
        self._data.track = cyclone

    def _compare_data(self, data_a: TropicalCyclone, data_b: TropicalCyclone) -> bool:
        return data_a.track.equals(data_b.track)
