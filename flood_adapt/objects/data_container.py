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

    @field_validator("path", mode="after")
    @classmethod
    def _absolute_path_if_provided(cls, value: Path | None) -> Path | None:
        if value is not None:
            if not value.is_absolute():
                raise ValueError(f"Path must be absolute: {value}.")
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
    def read(self, **kwargs) -> None:
        """Read the data from `path` into `_data`.

        Subclasses must implement this method.
        """
        ...

    @abstractmethod
    def write(self, output_dir: Path | None = None, **kwargs) -> None:
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
        if not self.has_data():
            self.read()
        return self._data

    def set_data(self, data: T) -> None:
        """Set the in-memory data object manually."""
        self._data = data

    def has_data(self) -> bool:
        """Check if data is currently loaded in memory."""
        return self._data is not None

    def _assert_path_exists(self, error_msg: str | None = "") -> None:
        """Check if the path exists on disk."""
        if self.path is None:
            raise ValueError("Path is not defined.")
        elif not self.path.exists():
            raise FileNotFoundError(error_msg or f"Path does not exist: {self.path}")

    def _assert_has_data(self) -> None:
        """Check if data is loaded in memory."""
        if self.data is None:
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

    def read(self, **kwargs) -> None:
        self._assert_path_exists(f"GeoDataFrame file not found: {self.path}")
        gdf = gpd.read_file(self.path, **kwargs)
        if gdf.crs is None:
            logger.warning(f"No CRS defined in {self.path}, assuming EPSG:4326")
            gdf = gdf.set_crs(epsg=4326)
        else:
            gdf = gdf.to_crs(epsg=4326)
        self._data = gdf

    def write(self, output_dir: Path | None = None, **kwargs) -> None:
        self._assert_has_data()
        write_path = output_dir / self.file_name if output_dir else self.path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        self.data.to_file(write_path, **kwargs)

    def _compare_data(self, data_a: gpd.GeoDataFrame, data_b: gpd.GeoDataFrame) -> bool:
        return data_a.equals(data_b)


class NetCDFContainer(DataContainer[xr.Dataset]):
    """Reference to a NetCDF dataset on disk."""

    _extension: ClassVar[str] = ".nc"

    def read(self, **kwargs) -> None:
        self._assert_path_exists(f"NetCDF file not found: {self.path}")
        self._data = xr.load_dataset(self.path, **kwargs)

    def write(self, output_dir: Path | None = None, **kwargs) -> None:
        self._assert_has_data()
        write_path = output_dir / self.file_name if output_dir else self.path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        self.data.to_netcdf(write_path, **kwargs)

    def _compare_data(self, data_a: xr.Dataset, data_b: xr.Dataset) -> bool:
        return data_a.equals(data_b)


class DataFrameContainer(DataContainer[pd.DataFrame]):
    """Reference to a pandas DataFrame stored on disk (CSV, Parquet, etc.)."""

    _extension: ClassVar[str] = ".csv"

    def read(self, **kwargs) -> None:
        self._assert_path_exists(f"DataFrame file not found: {self.path}")

        # Determine file format from extension
        suffix = self.path.suffix.lower()
        if suffix == ".csv":
            df = pd.read_csv(self.path, **kwargs)
        elif suffix in (".parquet", ".pq"):
            df = pd.read_parquet(self.path, **kwargs)
        elif suffix in (".feather", ".ftr"):
            df = pd.read_feather(self.path, **kwargs)
        else:
            raise ValueError(f"Unsupported DataFrame format: {suffix}")

        self._data = df

    def write(self, output_dir: Path | None = None, **kwargs) -> None:
        self._assert_has_data()
        write_path = output_dir / self.file_name if output_dir else self.path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = write_path.suffix.lower()

        if suffix == ".csv":
            self._data.to_csv(write_path, index=False, **kwargs)
        elif suffix in (".parquet", ".pq"):
            self._data.to_parquet(write_path, **kwargs)
        elif suffix in (".feather", ".ftr"):
            self._data.to_feather(write_path, **kwargs)
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

    def read(self, **kwargs) -> None:
        self._assert_path_exists(f"Cyclone track file not found: {self.path}")
        self._data = TropicalCyclone()
        self._data.read_track(self.path, fmt="ddb_cyc", **kwargs)

    def write(self, output_dir: Path | None = None, **kwargs) -> None:
        self._assert_has_data()
        write_path = output_dir / self.file_name if output_dir else self.path
        write_path.parent.mkdir(parents=True, exist_ok=True)
        self.data.write_track(write_path, fmt="ddb_cyc", **kwargs)

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
