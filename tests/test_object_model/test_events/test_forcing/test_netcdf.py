from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from flood_adapt.object_model.hazard.forcing.netcdf import validate_netcdf_forcing
from flood_adapt.object_model.hazard.interface.models import TimeModel


def get_test_dataset(
    lat: int = -80,
    lon: int = 32,
    time: TimeModel = TimeModel(time_step=timedelta(hours=1)),
    excluded_coord: Optional[str] = None,
    data_vars=["wind10_u", "wind10_v", "press_msl", "precip"],
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

    coords = {
        "time": _time,
        "lat": _lat,
        "lon": _lon,
    }
    if excluded_coord:
        coords.pop(excluded_coord)
    dims = list(coords.keys())

    def _generate_data(dimensions):
        shape = tuple(len(coords[dim]) for dim in dimensions if dim in coords)
        return gen.random(shape)

    _data_vars = {name: (dims, _generate_data(dims)) for name in data_vars}

    ds = xr.Dataset(
        data_vars=_data_vars,
        coords=coords,
        attrs={
            "crs": 4326,
        },
    )
    ds.raster.set_crs(4326)

    return ds


def test_all_datavars_all_coords():
    # Arrange
    vars = ["wind10_u", "wind10_v", "press_msl", "precip"]
    required_vars = set(vars)

    coords = {"time", "lat", "lon"}
    required_coords = coords

    ds = get_test_dataset(
        excluded_coord=None,
        data_vars=vars,
    )

    # Act
    result = validate_netcdf_forcing(
        ds, required_vars=required_vars, required_coords=required_coords
    )

    # Assert
    assert result.equals(ds)


def test_missing_datavar_all_coords_raises_validation_error():
    # Arrange
    vars = ["wind10_u", "wind10_v", "press_msl", "precip"]
    required_vars = set(vars)
    required_vars.add("missing_var")

    coords = {"time", "lat", "lon"}
    required_coords = coords

    ds = get_test_dataset(
        excluded_coord=None,
        data_vars=vars,
    )

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(
            ds, required_vars=required_vars, required_coords=required_coords
        )

    # Assert
    assert "missing_var" in str(e.value)
    assert "Missing required variables for netcdf forcing:" in str(e.value)


@pytest.mark.parametrize("excluded_coord", ["time", "lat", "lon"])
def test_all_datavar_missing_coords_raises_validation_error(excluded_coord):
    vars = ["wind10_u", "wind10_v", "press_msl", "precip"]
    required_vars = set(vars)

    coords = {"time", "lat", "lon"}
    required_coords = coords.copy()
    coords.remove(excluded_coord)

    ds = get_test_dataset(excluded_coord=excluded_coord, data_vars=vars)

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(
            ds, required_vars=required_vars, required_coords=required_coords
        )

    # Assert
    assert "Missing required coordinates for netcdf forcing:" in str(e.value)
    assert excluded_coord in str(e.value)


def test_netcdf_timestep_less_than_1_hour_raises():
    # Arrange
    vars = ["wind10_u", "wind10_v", "press_msl", "precip"]
    required_vars = set(vars)

    coords = {"time", "lat", "lon"}
    required_coords = coords

    ds = get_test_dataset(
        time=TimeModel(time_step=timedelta(minutes=30)),
        excluded_coord=None,
        data_vars=vars,
    )

    # Act
    with pytest.raises(ValueError) as e:
        validate_netcdf_forcing(
            ds, required_vars=required_vars, required_coords=required_coords
        )

    # Assert
    assert "SFINCS NetCDF forcing time step cannot be less than 1 hour" in str(e.value)
