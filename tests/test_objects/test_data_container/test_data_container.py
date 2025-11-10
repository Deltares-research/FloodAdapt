from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from shapely.geometry import Point

from flood_adapt.objects.data_container import (
    CycloneTrackContainer,
    DataFrameContainer,
    GeoDataFrameContainer,
    NetCDFContainer,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def sample_dataframe() -> pd.DataFrame:
    return pd.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})


@pytest.fixture
def sample_geodataframe() -> gpd.GeoDataFrame:
    gdf = gpd.GeoDataFrame(
        {"id": [1, 2, 3]},
        geometry=[Point(0, 0), Point(1, 1), Point(2, 2)],
        crs="EPSG:4326",
    )
    return gdf


@pytest.fixture
def sample_netcdf(tmp_path: Path, get_rng: np.random.Generator) -> Path:
    ds = xr.Dataset(
        {"temperature": (("x", "y"), get_rng.random((3, 3)))},
        coords={"x": [0, 1, 2], "y": [0, 1, 2]},
    )
    nc_path = tmp_path / "test.nc"
    ds.to_netcdf(nc_path)
    return nc_path


@pytest.fixture
def sample_cyclone_track(test_data_dir: Path) -> Path:
    return test_data_dir / "IAN.cyc"


# -----------------------------------------------------------------------------
# DataFrameContainer
# -----------------------------------------------------------------------------
def test_dataframe_read_write_csv(tmp_path, sample_dataframe):
    csv_path = tmp_path / "data.csv"
    sample_dataframe.to_csv(csv_path, index=False)

    ref = DataFrameContainer(path=csv_path)
    ref.read()

    assert ref.has_data()
    pd.testing.assert_frame_equal(ref.data, sample_dataframe)

    # Test write to a new file
    out_path = tmp_path / "data_copy.csv"
    ref.path = out_path
    ref.write()
    assert out_path.exists()

    df_copy = pd.read_csv(out_path)
    pd.testing.assert_frame_equal(df_copy, sample_dataframe)


def test_dataframe_equality(sample_dataframe, tmp_path):
    path1 = tmp_path / "a.csv"
    sample_dataframe.to_csv(path1, index=False)
    ref1 = DataFrameContainer(path=path1)
    ref2 = DataFrameContainer(path=path1)

    # Reading loads data and equality should hold
    ref1.read()
    ref2.read()
    assert ref1 == ref2


def test_dataframe_unsupported_format(tmp_path):
    bad_path = tmp_path / "data.txt"
    bad_path.write_text("test")

    ref = DataFrameContainer(path=bad_path)
    with pytest.raises(ValueError, match="Unsupported DataFrame format"):
        ref.read()


# -----------------------------------------------------------------------------
# GeoDataFrameContainer
# -----------------------------------------------------------------------------
def test_geodataref_read_write(tmp_path, sample_geodataframe):
    shp_path = tmp_path / "points.geojson"
    sample_geodataframe.to_file(shp_path, driver="GeoJSON")

    ref = GeoDataFrameContainer(path=shp_path)
    ref.read()
    assert isinstance(ref.data, gpd.GeoDataFrame)
    assert ref.has_data()

    # Write and re-read to confirm equality
    out_path = tmp_path / "points_copy.geojson"
    ref.path = out_path
    ref.write()
    ref2 = GeoDataFrameContainer(path=out_path)
    ref2.read()

    assert ref == ref2


# TODO add test with shapefiles ?


def test_geodataref_missing_file(tmp_path):
    ref = GeoDataFrameContainer(path=tmp_path / "missing.geojson")
    with pytest.raises(FileNotFoundError):
        ref.read()


# -----------------------------------------------------------------------------
# NetCDFContainer
# -----------------------------------------------------------------------------
def test_netcdfref_read_write(tmp_path, sample_netcdf):
    ref = NetCDFContainer(path=sample_netcdf)
    ref.read()

    assert isinstance(ref.data, xr.Dataset)
    assert "temperature" in ref.data.variables

    out_path = tmp_path / "copy.nc"
    ref.path = out_path
    ref.write()
    assert out_path.exists()

    ref2 = NetCDFContainer(path=out_path)
    ref2.read()

    assert ref == ref2


def test_netcdfref_missing_file(tmp_path):
    ref = NetCDFContainer(path=tmp_path / "does_not_exist.nc")
    with pytest.raises(FileNotFoundError):
        ref.read()


# -----------------------------------------------------------------------------
# CycloneTrackContainer
# -----------------------------------------------------------------------------
def test_cyclone_track_read_write(tmp_path: Path, sample_cyclone_track: Path):
    ref1 = CycloneTrackContainer(path=sample_cyclone_track)
    ref1.read()

    assert isinstance(ref1._data, TropicalCyclone)
    out_path = tmp_path / "IAN_copy.ddb_cyc"
    ref1.path = out_path
    ref1.write()
    assert out_path.exists()

    ref2 = CycloneTrackContainer(path=out_path)
    ref2.read()

    assert ref1 == ref2
