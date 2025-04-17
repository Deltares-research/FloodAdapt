import numpy as np
import pandas as pd
import xarray as xr


@staticmethod
def validate_netcdf_forcing(
    ds: xr.Dataset, required_vars: tuple[str, ...], required_coords: tuple[str, ...]
) -> xr.Dataset:
    """Validate a forcing dataset by checking for required variables and coordinates."""
    # Check variables
    _required_vars = set(required_vars)
    if not _required_vars.issubset(ds.data_vars):
        missing_vars = _required_vars - set(ds.data_vars)
        raise ValueError(
            f"Missing required variables for netcdf forcing: {missing_vars}"
        )

    # Check coordinates
    _required_coords = set(required_coords)
    if not _required_coords.issubset(ds.coords):
        missing_coords = _required_coords - set(ds.coords)
        raise ValueError(
            f"Missing required coordinates for netcdf forcing: {missing_coords}"
        )

    # Check time step
    ts = pd.to_timedelta(np.diff(ds.time).mean())
    if ts < pd.to_timedelta("1H"):
        raise ValueError(
            f"SFINCS NetCDF forcing time step cannot be less than 1 hour: {ts}"
        )

    for var in ds.data_vars:
        # Check order of dimensions
        if ds[var].dims != required_coords:
            raise ValueError(
                f"Order of dimensions for variable {var} must be {required_coords}"
            )
    return ds
