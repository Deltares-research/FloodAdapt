import logging
import math
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
    field_serializer,
    field_validator,
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
    _extension: ClassVar[str]

    # --- Validation and initialization ---

    @field_validator("path", mode="before")
    def _convert_str_to_path(cls, value: Path | str | None) -> Path | None:
        if isinstance(value, str):
            return Path(value)
        return value

    @model_validator(mode="after")
    def _validate_abs_path_exists(self) -> "DataContainer":
        if self.path is not None:
            if self.path.is_absolute() and not self.path.exists():
                raise FileNotFoundError(f"Path does not exist: {self.path}")
        return self

    @model_validator(mode="after")
    def _overwrite_default_name_from_path(self) -> "DataContainer":
        if (
            self.name == DataContainer.model_fields["name"].default
            and self.path is not None
        ):
            self.name = Path(self.path).stem
        return self

    def read(self, directory: Path | None = None, **kwargs) -> None:
        """Read the data from `path` into `_data`.

        If `directory` is provided and `path` is relative, it is resolved against `directory`.
        """
        if not self.path.is_absolute() and directory is not None:
            path = directory / self.path
        else:
            path = self.path
        self._assert_path_exists(path)

        self._data = self._deserialize(path, **kwargs)

    def write(self, output_dir: Path | None = None, **kwargs) -> None:
        """Write `_data` to the given directory or its original path."""
        self.data  # attempt to load data if not already loaded
        self._assert_has_data()
        write_path = output_dir / self.file_name if output_dir else self.path
        write_path.parent.mkdir(parents=True, exist_ok=True)

        self._serialize(write_path, **kwargs)

        if self.path is None:
            self.path = write_path

    # --- Abstract methods ---
    @abstractmethod
    def _serialize(self, path: Path, **kwargs) -> None:
        """Write `_data` to the given path.

        Subclasses must implement this method.
        """
        ...

    @abstractmethod
    def _deserialize(self, path: Path, **kwargs) -> T:
        """Read data from the given path and return it.

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
        if not self.has_data():
            self.read()
        return self._data

    def set_data(self, data: T) -> None:
        """Set the in-memory data object manually."""
        self._data = data

    def has_data(self) -> bool:
        """Check if data is currently loaded in memory."""
        return self._data is not None

    @staticmethod
    def _assert_path_exists(path: Path) -> None:
        """Check if the path exists on disk."""
        if path is None:
            raise ValueError("Path is not defined.")
        elif not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

    def _assert_has_data(self) -> None:
        """Check if data is loaded in memory."""
        if self._data is None:
            raise ValueError("No data loaded to write.")

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return False

        # This loads data if not already loaded
        if not self._compare_data(self.data, other.data):
            return False

        return True

    @property
    def file_name(self) -> str:
        """Get the filename of the data file."""
        if self.path is None:
            ext = (
                self._extension
                if self._extension.startswith(".")
                else f".{self._extension}"
            )
            return f"{self.name}{ext}"
        return self.path.name

    # --- Serialization ---
    @field_serializer("path")
    def serialize_path(self, path: Path | None) -> str:
        """Serialize the path as a string."""
        return self.file_name


class GeoDataFrameContainer(DataContainer[gpd.GeoDataFrame]):
    """Reference to a GeoDataFrame on disk."""

    _extension: ClassVar[str] = ".geojson"

    def _deserialize(self, path: Path, **kwargs) -> None:
        gdf = gpd.read_file(path, **kwargs)

        if gdf.crs is None:
            logger.warning(f"No CRS defined in {self.path}, assuming EPSG:4326")
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)

        return gdf

    def _serialize(self, path: Path, **kwargs) -> None:
        self.data.to_file(path, **kwargs)

    def _compare_data(self, data_a: gpd.GeoDataFrame, data_b: gpd.GeoDataFrame) -> bool:
        return data_a.equals(data_b)


class NetCDFContainer(DataContainer[xr.Dataset]):
    """Reference to a NetCDF dataset on disk."""

    _extension: ClassVar[str] = ".nc"

    def _deserialize(self, path: Path, **kwargs) -> xr.Dataset:
        return xr.load_dataset(path, **kwargs)

    def _serialize(self, path: Path, **kwargs) -> None:
        self.data.to_netcdf(path, **kwargs)

    def _compare_data(self, data_a: xr.Dataset, data_b: xr.Dataset) -> bool:
        return data_a.equals(data_b)


class DataFrameContainer(DataContainer[pd.DataFrame]):
    """Reference to a pandas DataFrame stored on disk (CSV, Parquet, etc.)."""

    _extension: ClassVar[str] = ".csv"

    def _serialize(self, path: Path, **kwargs) -> None:
        suffix = path.suffix.lower()

        if suffix == ".csv":
            self.data.to_csv(path, index=False, **kwargs)
        elif suffix in (".parquet", ".pq"):
            self.data.to_parquet(path, **kwargs)
        elif suffix in (".feather", ".ftr"):
            self.data.to_feather(path, **kwargs)
        else:
            raise ValueError(f"Unsupported DataFrame format for writing: {suffix}")

    def _deserialize(self, path: Path, **kwargs) -> pd.DataFrame:
        suffix = path.suffix.lower()

        if suffix == ".csv":
            return pd.read_csv(path, **kwargs)
        elif suffix in (".parquet", ".pq"):
            return pd.read_parquet(path, **kwargs)
        elif suffix in (".feather", ".ftr"):
            return pd.read_feather(path, **kwargs)
        else:
            raise ValueError(f"Unsupported DataFrame format for reading: {suffix}")

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

    def _deserialize(self, path: Path, **kwargs) -> TropicalCyclone:
        cyclone = TropicalCyclone()
        cyclone.read_track(path, fmt="ddb_cyc", **kwargs)
        return cyclone

    def _serialize(self, path: Path, **kwargs) -> None:
        self.data.write_track(path, fmt="ddb_cyc", **kwargs)

    def to_spw(
        self,
        directory: Path | None = None,
        include_rainfall: bool = True,
        recreate: bool = True,
    ) -> Path:
        self._assert_has_data()
        out_path = directory / self.path.name if directory else self.path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path = out_path.with_suffix(".spw")
        self.data.include_rainfall = include_rainfall
        if recreate:
            out_path.unlink(missing_ok=True)
        if not out_path.exists():
            self.data.to_spiderweb(filename=out_path)
        return out_path

    def translate_track(self, translation: TranslationModel) -> None:
        if self.data is None:
            raise ValueError("Cannot translate undefined track")

        if math.isclose(translation.eastwest_translation.value, 0) and math.isclose(
            translation.northsouth_translation.value, 0
        ):
            return

        logger.info(f"Translating the track of the tropical cyclone `{self.name}`")
        cyclone = self.data.track.to_crs(epsg=4326)

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
        self.data.track = cyclone

    def _compare_data(self, data_a: TropicalCyclone, data_b: TropicalCyclone) -> bool:
        return data_a.track.equals(data_b.track)
