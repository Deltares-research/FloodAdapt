from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from flood_adapt.objects.data_container import (
    NetCDFContainer,
)


@pytest.fixture
def sample_netcdf(tmp_path: Path, get_rng: np.random.Generator) -> Path:
    ds = xr.Dataset(
        {"temperature": (("x", "y"), get_rng.random((3, 3)))},
        coords={"x": [0, 1, 2], "y": [0, 1, 2]},
    )
    nc_path = tmp_path / "test.nc"
    ds.to_netcdf(nc_path)
    return nc_path


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


def test_netcdf_variables_preserved(tmp_path, sample_netcdf):
    ref = NetCDFContainer(path=sample_netcdf)
    ref.read()

    original = xr.load_dataset(sample_netcdf)

    assert set(ref.data.variables) == set(original.variables)


def test_netcdf_coordinates_preserved(tmp_path, sample_netcdf):
    ref = NetCDFContainer(path=sample_netcdf)
    ref.read()

    original = xr.load_dataset(sample_netcdf)

    assert ref.data.coords.keys() == original.coords.keys()


def test_netcdf_invalid_file_raises(tmp_path):
    bad_path = tmp_path / "bad.nc"
    bad_path.write_text("not a netcdf file")

    ref = NetCDFContainer(path=bad_path)

    with pytest.raises(Exception):
        ref.read()
