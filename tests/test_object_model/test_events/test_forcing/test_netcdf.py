from copy import copy
from datetime import timedelta

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.object_model.hazard.interface.models import TimeModel


@pytest.fixture
def required_vars():
    return ("wind10_u", "wind10_v", "press_msl", "precip")


@pytest.fixture
def required_coords():
    return ("time", "lat", "lon")


def get_test_dataset(
    lat: int = -80,
    lon: int = 32,
    time: TimeModel = TimeModel(time_step=timedelta(hours=1)),
    coords: tuple[str, ...] = ("time", "lat", "lon"),
    data_vars: tuple[str, ...] = ("wind10_u", "wind10_v", "press_msl", "precip"),
) -> xr.Dataset:
    gen = np.random.default_rng(42)

    _lat = np.arange(lat - 10, lat + 10, 1)
    _lon = np.arange(lon - 10, lon + 10, 1)
    _time = pd.date_range(
        start=time.start_time,
        end=time.end_time,
        freq=time.time_step,
        name="time",
    )

    _coords = {
        "time": _time,
        "lat": _lat,
        "lon": _lon,
    }
    coords_dict = {name: _coords.get(name, np.arange(10)) for name in coords}

    def _generate_data(dimensions):
        shape = tuple(len(coords_dict[dim]) for dim in dimensions if dim in coords_dict)
        return gen.random(shape)

    _data_vars = {name: (coords, _generate_data(coords)) for name in data_vars}

    ds = xr.Dataset(
        data_vars=_data_vars,
        coords=coords_dict,
        attrs={
            "crs": 4326,
        },
    )
    ds.raster.set_crs(4326)

    return ds


def test_all_datavars_all_coords(required_vars, required_coords):
    # Arrange
    ds = get_test_dataset()

    # Act
    result = validate_netcdf_forcing(
        ds, required_vars=required_vars, required_coords=required_coords
    )

    # Assert
    assert result.equals(ds)


def test_missing_datavar_all_coords_raises_validation_error(
    required_coords, required_vars
):
    # Arrange
    vars = tuple(copy(required_vars) + ("missing_var",))
    ds = get_test_dataset(data_vars=required_vars)

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(ds, required_vars=vars, required_coords=required_coords)

    # Assert
    assert "missing_var" in str(e.value)
    assert "Missing required variables for netcdf forcing:" in str(e.value)


def test_all_datavar_missing_coords_raises_validation_error(
    required_vars, required_coords
):
    # Arrange
    coords = tuple(copy(required_coords) + ("missing_coord",))
    ds = get_test_dataset(coords=required_coords, data_vars=required_vars)

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(ds, required_vars=required_vars, required_coords=coords)

    # Assert
    assert "Missing required coordinates for netcdf forcing:" in str(e.value)
    assert "missing_coord" in str(e.value)


def test_netcdf_timestep_less_than_1_hour_raises(required_vars, required_coords):
    # Arrange
    ds = get_test_dataset(
        time=TimeModel(time_step=timedelta(minutes=30)),
    )

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(
            ds, required_vars=required_vars, required_coords=required_coords
        )

    # Assert
    assert "SFINCS NetCDF forcing time step cannot be less than 1 hour" in str(e.value)


def test_netcdf_incorrect_coord_order_raises(required_vars, required_coords):
    # Arrange
    ds = get_test_dataset(
        coords=required_coords[::-1],  # reverse order
        data_vars=required_vars,
    )

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(
            ds, required_vars=required_vars, required_coords=required_coords
        )

    # Assert
    assert "Order of dimensions for variable" in str(e.value)
    assert f"must be {tuple(required_coords)}" in str(e.value)
