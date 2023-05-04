# -*- coding: utf-8 -*-
"""
Created on Thu May 20 10:32:33 2021

@author: ormondt
"""

import os
from datetime import datetime

import numpy as np
import pandas as pd
import xarray as xr
from pyproj import CRS


class Dataset:
    def __init__(self):
        self.quantity = None
        self.unit = None
        self.time = []
        self.x = None
        self.y = None
        self.crs = None
        self.val = None
        self.u = None
        self.v = None


def download(
    param_list, lon_range, lat_range, path, prefix, time_range=None, times=None
):
    if times is not None:
        requested_times = times
        time_range = [times[0], times[-1]]
    else:
        requested_times = (
            pd.date_range(start=time_range[0], end=time_range[1], freq="3H")
            .to_pydatetime()
            .tolist()
        )

    ntime = len(requested_times)

    datasets = []
    for param in param_list:
        dataset = Dataset()
        dataset.crs = CRS.from_epsg(4326)
        dataset.quantity = param
        datasets.append(dataset)

    icont = False
    # Get lat,lon
    for it, time in enumerate(requested_times):
        try:
            h = requested_times[it].hour
            month_string = requested_times[it].strftime("%Y%m")
            date_string = requested_times[it].strftime("%Y%m%d")

            toldnew = datetime(2020, 5, 15, 0, 0, 0, 0)
            cstr = "0000_000"

            if time < toldnew:
                # Analysis data before May 15th, 2020 stored in different url
                base_url = "https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-g4-anl-files-old/"
                url = base_url + month_string + "/" + date_string + "/"
                name = "gfsanl_4_" + date_string + "_" + cstr + ".grb2"
            else:
                base_url = (
                    "https://www.ncei.noaa.gov/thredds/dodsC/model-gfs-g4-anl-files/"
                )
                url = base_url + month_string + "/" + date_string + "/"
                name = "gfs_4_" + date_string + "_" + cstr + ".grb2"

            # try:
            #     gfs   = TDSCatalog(url)
            # except:
            #     gfs   = []
            # okay = False
            # if gfs:
            #     for j, ds in enumerate(gfs.datasets):
            #         if ds==name:
            #             okay = True
            #             break
            # if not okay:
            #     # Try the next time
            #     continue

            ds = xr.open_dataset(url + name)  # or engine='pydap'

            lon_range[0] = np.mod(lon_range[0], 360.0)
            lon_range[1] = np.mod(lon_range[1], 360.0)

            i1 = np.where(ds.lat.values > lat_range[1])[0][-1]
            i2 = np.where(ds.lat.values < lat_range[0])[0][0]
            j1 = np.where(ds.lon.values < lon_range[0])[0][-1]
            j2 = np.where(ds.lon.values > lon_range[1])[0][0]

            # Latitude and longitude
            lat = ds.lat.values[i1:i2]
            lon = ds.lon.values[j1:j2]

            nrows = len(lat)
            ncols = len(lon)

            # ncss  = gfs.datasets[j].subset()
            # query = ncss.query()
            # query.lonlat_box(north=lat_range[1], \
            #                  south=lat_range[0], \
            #                   east=lon_range[1],  \
            #                   west=lon_range[0]).vertical_level(10.0)
            # query.variables("u-component_of_wind_height_above_ground",
            #                 "v-component_of_wind_height_above_ground")
            # data = ncss.get_data(query)
            # data = xr.open_dataset(NetCDF4DataStore(data))
            # lon = np.array(data['lon'])
            # lat = np.array(data['lat'])

            # nrows = len(lat)
            # ncols = len(lon)

            # Latitude and longitude found, so we can stop now
            icont = True
            break

        except:
            # Try another time
            pass

    if not icont:
        # Could not find any data
        print("Could not find any data in requested range !")
        datasets = []
        return datasets

    # initialize matrices
    for dataset in datasets:
        dataset.x = lon
        dataset.y = lat
        if dataset.quantity == "wind":
            dataset.u = np.empty((ntime, nrows, ncols))
            dataset.u[:] = np.NaN
            dataset.v = np.empty((ntime, nrows, ncols))
            dataset.v[:] = np.NaN
        else:
            dataset.val = np.empty((ntime, nrows, ncols))
            dataset.val[:] = np.NaN

    for it, time in enumerate(requested_times):
        h = time.hour
        month_string = time.strftime("%Y%m")
        date_string = time.strftime("%Y%m%d")
        url = base_url + month_string + "/" + date_string + "/"

        # try:
        #     gfs   = TDSCatalog(url)
        # except:
        #     print("Could not fetch catalogue")
        #     continue

        if h == 0:
            cstr = "0000_000"
            crstr = "0000_003"
            var_prcp = "Total_precipitation_surface_3_Hour_Accumulation"
        elif h == 3:
            cstr = "0000_003"
            crstr = "0000_006"
            var_prcp = "Total_precipitation_surface_6_Hour_Accumulation"
        elif h == 6:
            cstr = "0600_000"
            crstr = "0600_003"
            var_prcp = "Total_precipitation_surface_3_Hour_Accumulation"
        elif h == 9:
            cstr = "0600_003"
            crstr = "0600_006"
            var_prcp = "Total_precipitation_surface_6_Hour_Accumulation"
        elif h == 12:
            cstr = "1200_000"
            crstr = "1200_003"
            var_prcp = "Total_precipitation_surface_3_Hour_Accumulation"
        elif h == 15:
            cstr = "1200_003"
            crstr = "1200_006"
            var_prcp = "Total_precipitation_surface_6_Hour_Accumulation"
        elif h == 18:
            cstr = "1800_000"
            crstr = "1800_003"
            var_prcp = "Total_precipitation_surface_3_Hour_Accumulation"
        elif h == 21:
            cstr = "1800_003"
            crstr = "1800_006"
            var_prcp = "Total_precipitation_surface_6_Hour_Accumulation"
        else:
            print(
                "ERROR: cycle and cycle_last in xml-file can only be specified rounded off on 3 hour values!"
            )

        # Loop through requested parameters
        for ind, param in enumerate(param_list):
            dataset = datasets[ind]
            dataset.time.append(time)

            if param == "precipitation":
                if time < toldnew:
                    name = "gfsanl_4_" + date_string + "_" + crstr + ".grb2"
                else:
                    name = "gfs_4_" + date_string + "_" + crstr + ".grb2"

            else:
                if time < toldnew:
                    name = "gfsanl_4_" + date_string + "_" + cstr + ".grb2"
                else:
                    name = "gfs_4_" + date_string + "_" + cstr + ".grb2"

            try:
                okay = False
                # for j, ds in enumerate(gfs.datasets):
                #     if ds==name:
                #         okay = True
                #         break

                # if not okay:
                #     # File not found, on to the next parameter
                #     print("Warning! " + name + " was not found on server")
                #     makezeros = True
                #     #continue

                print(name + " : " + param)

                for iattempt in range(10):
                    try:
                        ds = xr.open_dataset(url + name)
                        if iattempt > 0:
                            print("Success at attempt no " + int(iattempt + 1))
                        #                            makezeros = False
                        okay = True
                        break
                    except:
                        # Try again
                        #                        makezeros = True
                        pass

                if okay:
                    if param == "wind":
                        u = ds["u-component_of_wind_height_above_ground"][
                            0, 0, i1:i2, j1:j2
                        ].values
                        v = ds["v-component_of_wind_height_above_ground"][
                            0, 0, i1:i2, j1:j2
                        ].values
                        dataset.u[it, :, :] = np.array(u)
                        dataset.v[it, :, :] = np.array(v)

                        # query = ncss.query()
                        # query.lonlat_box(north=lat_range[1], \
                        #                  south=lat_range[0], \
                        #                   east=lon_range[1],  \
                        #                   west=lon_range[0]).vertical_level(10.0)
                        # query.variables("u-component_of_wind_height_above_ground",
                        #                 "v-component_of_wind_height_above_ground")
                        # data = ncss.get_data(query)
                        # data = xr.open_dataset(NetCDF4DataStore(data))
                        # u = data['u-component_of_wind_height_above_ground']
                        # v = data['v-component_of_wind_height_above_ground']
                        # dataset.unit = u.units
                        # u = u.metpy.unit_array.squeeze()
                        # dataset.u[it,:,:] = np.array(u)
                        # v = v.metpy.unit_array.squeeze()
                        # dataset.v[it,:,:] = np.array(v)

                    else:
                        # Other scalar variables
                        #                fac = 1.0
                        if param == "barometric_pressure":
                            var_name = "Pressure_reduced_to_MSL_msl"
                        elif param == "precipitation":
                            var_name = var_prcp
                        val = ds[var_name][0, i1:i2, j1:j2].values
                        # #                    fac = 1.0
                        #                 query = ncss.query()
                        #                 query.lonlat_box(north=lat_range[1], \
                        #                                  south=lat_range[0], \
                        #                                  east=lon_range[1],  \
                        #                                  west=lon_range[0])
                        #                 query.variables(var_name)
                        #                 data = ncss.get_data(query)
                        #                 data = xr.open_dataset(NetCDF4DataStore(data))
                        #                 val          = data[var_name]
                        #                 dataset.unit = val.units
                        #                 val          = np.array(val.metpy.unit_array.squeeze())
                        if param == "precipitation":
                            # Data is stored either as 3-hourly (at 03h) or 6-hourly (at 06h) accumulated rainfall
                            # For the first, just divide by 3 to get hourly precip
                            # For the second, first subtract volume that fell in the first 3 hours
                            if h == 0 or h == 6 or h == 12 or h == 18:
                                val = val / 3  # Convert to mm/h
                            else:
                                val = (
                                    val - 3 * np.squeeze(dataset.val[it - 1, :, :])
                                ) / 3
                        dataset.val[it, :, :] = val

                else:
                    print("Could not get data ...")

                # elif makezeros: # add zeros
                #      if param == "wind":
                #          dataset.u[:] = 0.0
                #          dataset.v[:] = 0.0
                #          print(param + " was not found on server ... --> using 0.0 m/s instead !!!")

                #      if param == "precipitation":
                #          dataset.val[:] = 0
                #          print(param + " was not found on server ... --> using 0.0 m/s instead !!!")

                #      if param == "barometric_pressure":
                #          dataset.val[:] = 102000.0
                #          print(param + " was not found on server ... --> using 102000.0 Pa instead !!!")

            except:
                print("Could not download data")

        # Write data to netcdf
        time_string = time.strftime("%Y%m%d_%H%M")
        file_name = prefix + "." + time_string + ".nc"
        full_file_name = os.path.join(path, file_name)
        ds = xr.Dataset()

        okay = False
        for ind, dataset in enumerate(datasets):
            if dataset.quantity == "wind":
                uu = dataset.u[it, :, :]
                vv = dataset.v[it, :, :]

                if not np.any(np.isnan(uu)) and not np.any(np.isnan(vv)):
                    okay = True

                    da = xr.DataArray(
                        uu, coords=[("lat", dataset.y), ("lon", dataset.x)]
                    )
                    ds["wind_u"] = da

                    da = xr.DataArray(
                        vv, coords=[("lat", dataset.y), ("lon", dataset.x)]
                    )
                    ds["wind_v"] = da

                else:
                    print("NaNs found in wind. Skipping this time step.")

            else:
                val = dataset.val[it, :, :]

                if not np.any(np.isnan(val)):
                    okay = True

                    da = xr.DataArray(
                        val, coords=[("lat", dataset.y), ("lon", dataset.x)]
                    )
                    ds[dataset.quantity] = da

                else:
                    print(
                        "NaNs found in "
                        + dataset.quantity
                        + ". Skipping this time step."
                    )

        if okay:
            # Only write to file if there is any data
            ds.to_netcdf(path=full_file_name)
        else:
            print("No NetCDF file written for time " + time_string)

    return datasets


# Helper function for finding proper time variable
def find_time_var(var, time_basename="time"):
    for coord_name in var.coords:
        if coord_name.startswith(time_basename):
            return var.coords[coord_name]
    raise ValueError("No time variable found for " + var.name)


# Helper function for finding proper time variable
def find_height_var(var, time_basename="height"):
    for coord_name in var.coords:
        if coord_name.startswith(time_basename):
            return var.coords[coord_name]
    raise ValueError("No height variable found for " + var.name)
