import numpy as np
import pandas as pd
import xarray as xr


@staticmethod
def validate_netcdf_forcing(
    ds: xr.Dataset, required_vars: set[str], required_coords: set[str]
) -> xr.Dataset:
    """Validate a forcing dataset by checking for required variables and coordinates."""
    if not required_vars.issubset(ds.data_vars):
        missing_vars = required_vars - set(ds.data_vars)
        raise ValueError(
            f"Missing required variables for netcdf forcing: {missing_vars}"
        )
    if not required_coords.issubset(ds.coords):
        missing_coords = required_coords - set(ds.coords)
        raise ValueError(
            f"Missing required coordinates for netcdf forcing: {missing_coords}"
        )

    ts = pd.to_timedelta(np.diff(ds.time).mean())
    if ts < pd.to_timedelta("1H"):
        raise ValueError(
            f"SFINCS NetCDF forcing time step cannot be less than 1 hour: {ts}"
        )

    return ds
