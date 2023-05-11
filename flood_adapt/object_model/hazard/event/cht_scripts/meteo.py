# -*- coding: utf-8 -*-
"""
Created on Thu May 20 14:56:45 2021

@author: ormondt
"""

import datetime
import importlib
import os

import geopandas as gpd
import netCDF4 as nc
import numpy as np
import pandas as pd
import xarray as xr
from pyproj import Transformer
from scipy import interpolate
from shapely.geometry import Point

import flood_adapt.object_model.hazard.event.cht_scripts.fileops as fo
from flood_adapt.object_model.hazard.event.cht_scripts.misc_tools import interp2

# Added for TCs
from flood_adapt.object_model.hazard.event.cht_scripts.tropical_cyclone import (
    TropicalCyclone,
)

date_format = "%Y%m%d %H%M%S"


class MeteoSource:
    # e.g. GFS forecast
    def __init__(
        self,
        name,
        module_name,
        source_type,
        crs=None,
        long_name=None,
        delay=None,
        cycle_interval=6,
        time_interval=3,
    ):
        self.name = name
        if not long_name:
            self.long_name = name
        else:
            self.long_name = long_name
        self.module_name = module_name
        self.crs = crs
        self.type = source_type
        self.delay = delay
        self.cycle_interval = cycle_interval
        self.time_interval = time_interval


class MeteoMatrixScalar:
    def __init__(self):
        self.name = None
        self.val = None
        self.unit = None


class MeteoMatrixVector:
    def __init__(self):
        self.name = None
        self.u = None
        self.v = None
        self.unit = None


class MeteoGrid:
    # e.g. gfs_forecast_0p25_conus
    # includes parameters

    def __init__(
        self,
        name=None,
        source=None,
        parameters=None,
        path=None,
        x_range=None,
        y_range=None,
        long_name=None,
        crs=None,
        xystride=1,
        tstride=1,
        backup=None,
    ):
        self.name = name
        self.crs = crs
        if not long_name:
            self.long_name = name
        else:
            self.long_name = long_name
        self.source = source
        self.x_range = x_range
        self.y_range = y_range
        self.xystride = xystride
        self.tstride = tstride
        self.backup = backup

        if not parameters:
            self.parameters = ["wind", "barometric_pressure", "precipitation"]
        else:
            self.parameters = parameters
        self.path = path

        self.time = None
        self.x = None
        self.y = None
        self.quantity = []
        self.last_analysis_time = None

    def download(self, time_range, parameters=None, path=None):
        if not parameters:
            parameters = self.parameters

        if not path:
            path = self.path

        #        module = __import__(self.source.module_name)
        module = importlib.import_module(
            "flood_adapt.object_model.hazard.event.cht_scripts."
            + self.source.module_name
        )  # Changed by Tim de Wilde

        fo.mkdir(path)

        if self.source.type == "forecast":
            # Need to check on previous cycles

            # Round down to hour

            h0 = time_range[0].hour
            h0 = h0 - np.mod(h0, 6)
            t0 = time_range[0].replace(
                microsecond=0, second=0, minute=0, hour=h0, tzinfo=datetime.timezone.utc
            )

            t1 = time_range[1].replace(
                microsecond=0, second=0, minute=0, tzinfo=datetime.timezone.utc
            )

            # Current (last available) cycle
            t_current = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(hours=self.source.delay)
            h0 = t_current.hour
            h0 = h0 - np.mod(h0, 6)
            t_current = t_current.replace(microsecond=0, second=0, minute=0, hour=h0)

            t_last = t_current - datetime.timedelta(hours=6)

            t0 = min(t0, t_last)

            # Previous cycles
            previous_cycle_times = (
                pd.date_range(
                    start=t0, end=t_last, freq=str(self.source.cycle_interval) + "H"
                )
                .to_pydatetime()
                .tolist()
            )

            # Loop through previous cycles (which have the analyzed data)
            # to see if they are there
            for it, t in enumerate(previous_cycle_times):
                if t.replace(tzinfo=None) <= time_range[1]:
                    cycle_path = os.path.join(path, t.strftime("%Y%m%d_%Hz"))

                    # Check if both files (00h and 03h) are there
                    t0 = t
                    time_string = t.strftime("%Y%m%d_%H%M")
                    f0 = self.name + "." + time_string + ".nc"
                    f0 = os.path.join(cycle_path, f0)

                    t3 = t + datetime.timedelta(hours=3)
                    time_string = t3.strftime("%Y%m%d_%H%M")
                    f3 = self.name + "." + time_string + ".nc"
                    f3 = os.path.join(cycle_path, f3)

                    if not os.path.exists(f0) or not os.path.exists(f3):
                        # Download data
                        print(
                            "Downloading data from cycle : " + t.strftime("%Y%m%d_%Hz")
                        )
                        hrlast = self.source.cycle_interval - self.source.time_interval
                        data = module.download(
                            parameters,
                            self.x_range,
                            self.y_range,
                            [t, t + datetime.timedelta(hours=hrlast)],
                            t,
                        )
                        if not data and it > 0:
                            # Last cycle was not available !
                            # Try getting all the data from previous cycle
                            print(
                                "No data available in cycle "
                                + t.strftime("%Y%m%d_%Hz")
                                + ". Trying to bring in data from previous cycle "
                                + previous_cycle_times[it - 1].strftime("%Y%m%d_%Hz")
                            )
                            cycle_path = os.path.join(
                                path,
                                previous_cycle_times[it - 1].strftime("%Y%m%d_%Hz"),
                            )
                            data = module.download(
                                parameters,
                                self.x_range,
                                self.y_range,
                                [t.replace(tzinfo=None), time_range[1]],
                                previous_cycle_times[it - 1],
                            )

                        if data:
                            if not os.path.exists(cycle_path):
                                fo.mkdir(cycle_path)
                            self.save_to_nc(cycle_path, data)
                            self.last_analysis_time = t
                            for d in data:
                                try:
                                    actualsource = d.src
                                    if any("coamps" in src for src in actualsource):
                                        filename = os.path.join(
                                            cycle_path, "coamps_used.txt"
                                        )
                                        fid = open(filename, "w")
                                        fid.write(
                                            "Coamps data was used in this forecast \n"
                                        )
                                        fid.close()
                                        break
                                except:
                                    continue

            if t1 >= t_current:
                # And now download the forecast data (last available cycle)
                cycle_path = os.path.join(path, t_current.strftime("%Y%m%d_%Hz"))
                print(
                    "Downloading data from cycle : " + t_current.strftime("%Y%m%d_%Hz")
                )
                fo.mkdir(cycle_path)
                data = module.download(
                    parameters, self.x_range, self.y_range, [t_current, t1], t
                )
                for d in data:
                    try:
                        actualsource = d.src
                        if any("coamps" in src for src in actualsource):
                            filename = os.path.join(cycle_path, "coamps_used.txt")
                            fid = open(filename, "w")
                            fid.write("Coamps data was used in this forecast \n")
                            fid.close()
                            break
                    except:
                        continue

                self.save_to_nc(cycle_path, data)
                self.last_analysis_time = t_current

        else:
            # Much easier, but do NOT hardcode frequency!!!
            requested_times = (
                pd.date_range(start=time_range[0], end=time_range[1], freq="3H")
                .to_pydatetime()
                .tolist()
            )
            rtimes = []
            # Check which files do not yet exist
            for t in requested_times:
                time_string = t.strftime("%Y%m%d_%H%M")
                file_name = self.name + "." + time_string + ".nc"
                full_file_name = os.path.join(path, file_name)
                if not os.path.exists(full_file_name):
                    rtimes.append(t)

            if rtimes:
                data = module.download(
                    parameters,
                    self.x_range,
                    self.y_range,
                    path,
                    self.name,
                    times=rtimes,
                )

                for d in data:
                    try:
                        actualsource = d.src
                        if any("coamps" in src for src in actualsource):
                            filename = os.path.join(path, "coamps_used.txt")
                            fid = open(filename, "w")  # Why is there no path here?
                            fid.write("Coamps data was used in this hindcast \n")
                            fid.close()
                            break
                    except:
                        continue
            else:
                print("Requested meteo data already available")

    def save_to_nc(self, path, data):
        # Stick everything in one file for now
        for it, t in enumerate(data[0].time):
            time_string = t.strftime("%Y%m%d_%H%M")
            file_name = self.name + "." + time_string + ".nc"
            full_file_name = os.path.join(path, file_name)
            ds = xr.Dataset()

            for dd in data:
                if dd.quantity == "wind":
                    uu = dd.u[it, :, :]
                    da = xr.DataArray(uu, coords=[("lat", dd.y), ("lon", dd.x)])
                    #                    if dd.src[it]:
                    #                        da.attrs['source'] = dd.src[it]
                    if dd.src:
                        da.attrs["source"] = dd.src
                    ds["wind_u"] = da
                    vv = dd.v[it, :, :]
                    da = xr.DataArray(vv, coords=[("lat", dd.y), ("lon", dd.x)])
                    if dd.src:
                        da.attrs["source"] = dd.src
                    ds["wind_v"] = da
                else:
                    try:
                        val = dd.val[it, :, :]
                        da = xr.DataArray(val, coords=[("lat", dd.y), ("lon", dd.x)])
                        if dd.src:
                            da.attrs["source"] = dd.src
                        ds[dd.quantity] = da
                    except:
                        print("Could not write " + dd.quantity + " to file ...")

            ds.to_netcdf(path=full_file_name)

            ds.close()

    def collect(self, time_range, parameters=None, xystride=1, tstride=1):
        if not parameters:
            parameters = self.parameters

        # Merge data from netcdf files

        if self.source.type == "forecast":
            # requested_times = pd.date_range(start=time_range[0],
            #                           end=time_range[1],
            #                           freq='3H').to_pydatetime().tolist()
            requested_times = (
                pd.date_range(
                    start=time_range[0],
                    end=time_range[1],
                    freq=str(self.source.time_interval) + "H",
                )
                .to_pydatetime()
                .tolist()
            )
            requested_files = []
            for t in requested_times:
                requested_files.append(None)

            # Make list of all cyc
            all_cycle_paths = fo.list_folders(os.path.join(self.path, "*"))
            # Loop through all cycle paths
            for cycle_path in all_cycle_paths:
                t = datetime.datetime.strptime(cycle_path[-12:-1], "%Y%m%d_%H")
                # Check if path falls within requested range
                if t >= time_range[0] and t <= time_range[1]:
                    # Find all times available in this cycle
                    files_in_cycle = fo.list_files(os.path.join(cycle_path, "*.nc"))
                    for file in files_in_cycle:
                        t_file = datetime.datetime.strptime(file[-16:-3], "%Y%m%d_%H%M")
                        if t_file in requested_times:
                            ind = requested_times.index(t_file)
                            requested_files[ind] = file
                            self.last_analysis_time = t

            # Use earliest forecast file available for spinup (force earlier timesteps with this file)
            ID1 = next(i for i, v in enumerate(requested_files) if v is not None)
            for ind in range(ID1):
                requested_files[ind] = requested_files[ID1]

            for ind, file in enumerate(requested_files):
                if not file:
                    times_to_remove.append(requested_times[ind])

            # Get rid of None values
            times_to_remove = []
            for ind, file in enumerate(requested_files):
                if not file:
                    times_to_remove.append(requested_times[ind])
            if times_to_remove:
                for tr in times_to_remove:
                    requested_times.remove(tr)
            requested_files = [value for value in requested_files if value is not None]
            # Turn time array into nump array
            requested_times = np.array(requested_times)

        else:
            # requested_times = pd.date_range(start=time_range[0],
            #               end=time_range[1],
            #               freq='3H').to_pydatetime().tolist()

            requested_files = []
            requested_times = []
            files_in_cycle = fo.list_files(os.path.join(self.path, "*.nc"))
            #            for file in files_in_cycle:
            for ifile in range(0, len(files_in_cycle), tstride):
                file = files_in_cycle[ifile]
                t_file = datetime.datetime.strptime(file[-16:-3], "%Y%m%d_%H%M")
                if t_file >= time_range[0] and t_file <= time_range[1]:
                    requested_files.append(os.path.join(self.path, file))
                    requested_times.append(t_file)

        # And now loop through the files, read them and store them in large array
        self.time = np.array(requested_times)

        if not requested_files:
            print("No meteo data files found within requested time range")
            return

        # Read in first file to get dimensions
        dnc = nc.Dataset(requested_files[0])
        lon = dnc["lon"][0::xystride].data
        if lon[0] > 180.0:
            lon = lon - 360.0
        lat = dnc["lat"][0::xystride].data
        lat = np.flip(lat)
        nrows = len(lat)
        ncols = len(lon)
        ntime = len(requested_times)
        self.x = lon
        self.y = lat

        for ind, param in enumerate(parameters):
            if param == "wind":
                matrix = MeteoMatrixVector()
            else:
                matrix = MeteoMatrixScalar()

            matrix.name = param

            if param == "wind":
                matrix.u = np.empty((ntime, nrows, ncols))
                matrix.v = np.empty((ntime, nrows, ncols))
                matrix.u[:] = np.nan
                matrix.v[:] = np.nan
            else:
                matrix.val = np.empty((ntime, nrows, ncols))
                matrix.val[:] = np.nan

            for it, time in enumerate(requested_times):
                #                print("Reading " + requested_files[it] + " ...")
                dnc = nc.Dataset(requested_files[it])
                uuu = dnc["wind_u"]
                try:
                    if param == "wind":
                        uuu = dnc["wind_u"][:, :].data
                        vvv = dnc["wind_v"][:, :].data
                        uuu = np.flipud(uuu[0::xystride, 0::xystride])
                        vvv = np.flipud(vvv[0::xystride, 0::xystride])
                        matrix.u[it, :, :] = uuu
                        matrix.v[it, :, :] = vvv
                    #                        matrix.u[it,:,:] = np.flipud(dnc["wind_u"][0::xystride,0::xystride].data)
                    #                        matrix.v[it,:,:] = np.flipud(dnc["wind_v"][0::xystride,0::xystride].data)
                    else:
                        uuu = dnc[param][:, :].data
                        uuu = np.flipud(uuu[0::xystride, 0::xystride])
                        matrix.val[it, :, :] = uuu
                except:
                    print("Could not collect " + param + " from " + requested_files[it])

            self.quantity.append(matrix)

    def read_from_delft3d(self, file_name, crs=None):
        pass

    def write_to_delft3d(
        self,
        file_name,
        version="1.03",
        path=None,
        header_comments=False,
        refdate=None,
        parameters=None,
        time_range=None,
    ):
        if not refdate:
            refdate = self.time[0]

        if not time_range:
            time_range = [self.time[0], self.time[-1]]

        if not parameters:
            parameters = []
            for q in self.quantity:
                parameters.append(q.name)

        if self.crs.is_geographic:
            grid_unit = "degrees"
        else:
            grid_unit = "m"

        files = []
        for param in parameters:
            # Look up index of this parameter
            for ind, quant in enumerate(self.quantity):
                if param == quant.name:
                    q = self.quantity[ind]
                    break
            if param == "wind":
                file = {}
                file["data"] = q.u
                file["ext"] = "amu"
                file["quantity"] = "x_wind"
                file["unit"] = "m s-1"
                file["fmt"] = "%6.1f"
                files.append(file)
                file = {}
                file["data"] = q.v
                file["ext"] = "amv"
                file["quantity"] = "y_wind"
                file["unit"] = "m s-1"
                file["fmt"] = "%6.1f"
                files.append(file)
            elif param == "barometric_pressure":
                file = {}
                file["data"] = q.val
                file["ext"] = "amp"
                file["quantity"] = "air_pressure"
                file["unit"] = "Pa"
                file["fmt"] = "%7.0f"
                files.append(file)
            elif param == "precipitation":
                file = {}
                file["data"] = q.val
                file["ext"] = "ampr"
                file["quantity"] = "precipitation"
                file["unit"] = "mm h-1"
                file["fmt"] = "%7.1f"
                files.append(file)

        # if self.quantity == "x_wind":
        #     unit = "m s-1"
        #     ext  = "amu"
        #     fmt  = "%6.1f"
        # elif self.quantity == "y_wind":
        #     unit = "m s-1"
        #     ext  = "amv"
        #     fmt  = "%6.1f"
        # elif self.quantity == "air_pressure":
        #     unit = "Pa"
        #     ext  = "amp"
        #     fmt  = "%7.0f"
        # elif self.quantity == "air_temperature":
        #     unit = "Celsius"
        #     ext  = "amt"
        #     fmt  = "%7.1f"
        # elif self.quantity == "relative_humidity":
        #     unit = "%"
        #     ext  = "amr"
        #     fmt  = "%7.1f"
        # elif self.quantity == "cloudiness":
        #     unit = "%"
        #     ext  = "amc"
        #     fmt  = "%7.1f"
        # elif self.quantity == "sw_radiation_flux":
        #     unit = "W/m2"
        #     ext  = "ams"
        #     fmt  = "%7.1f"
        # elif self.quantity == "precipitation":
        #     unit = "mm/h"
        #     ext  = "ampr"
        #     fmt  = "%7.1f"

        for file in files:
            ncols = len(self.x)
            nrows = len(self.y)

            dx = (self.x[-1] - self.x[0]) / (len(self.x) - 1)
            dy = (self.y[-1] - self.y[0]) / (len(self.y) - 1)

            if path:
                full_file_name = os.path.join(path, file_name + "." + file["ext"])
            else:
                full_file_name = file_name + "." + file["ext"]

            fid = open(full_file_name, "w")

            if header_comments:
                fid.write("### START OF HEADER\n")
                fid.write(
                    "### All text on a line behind the first # is parsed as commentary\n"
                )
                fid.write("### Additional commments\n")

            fid.write(
                "FileVersion      =   "
                + version
                + "                                               # Version of meteo input file, to check if the newest file format is used\n"
            )
            fid.write(
                "filetype         =   meteo_on_equidistant_grid                          # Type of meteo input file: meteo_on_flow_grid, meteo_on_equidistant_grid, meteo_on_curvilinear_grid or meteo_on_spiderweb_grid\n"
            )
            fid.write(
                "NODATA_value     =   -999                                               # Value used for undefined or missing data\n"
            )
            fid.write("n_cols           =   " + str(ncols) + "\n")
            fid.write("n_rows           =   " + str(nrows) + "\n")
            fid.write("grid_unit        =   " + grid_unit + "\n")
            #            fid.write("x_llcorner       =   " + str(min(self.x)) + "\n")
            #            fid.write("y_llcorner       =   " + str(min(self.y)) + "\n")
            fid.write("x_llcorner       =   " + str(min(self.x) - 0.5 * dx) + "\n")
            fid.write("y_llcorner       =   " + str(min(self.y) - 0.5 * dy) + "\n")
            if version == "1.02":
                fid.write("value_pos       =    corner\n")
            fid.write("dx               =   " + str(dx) + "\n")
            fid.write("dy               =   " + str(dy) + "\n")
            fid.write(
                "n_quantity       =   1                                                  # Number of quantities prescribed in the file\n"
            )
            fid.write("quantity1        =   " + file["quantity"] + "\n")
            fid.write("unit1            =   " + file["unit"] + "\n")
            if header_comments:
                fid.write("### END OF HEADER\n")

            # Add extra blocks if data does not cover time range
            if self.time[0] > time_range[0]:
                dt = time_range[0] - refdate
                tim = dt.total_seconds() / 60
                val = np.flipud(file["data"][0, :, :])
                # Skip blocks with only nans
                if not np.all(np.isnan(val)):
                    val[val == np.nan] = -999.0
                    fid.write(
                        "TIME = "
                        + str(tim)
                        + " minutes since "
                        + refdate.strftime("%Y-%m-%d %H:%M:%S")
                        + " +00:00\n"
                    )
                    np.savetxt(fid, val, fmt=file["fmt"])

            for it, time in enumerate(self.time):
                dt = time - refdate
                tim = dt.total_seconds() / 60
                val = np.flipud(file["data"][it, :, :])

                if param == "wind":
                    if np.max(val) > 1000.0:
                        val = np.zeros_like(
                            val
                        )  # Weird array, don't trust. Set everything to zeros.
                        val[np.where(val == 0.0)] = np.nan
                        print(
                            "Warning! Wind speed > 1000 m/s at "
                            + time.strftime("%Y-%m-%d %H:%M:%S")
                            + " !"
                        )
                    if np.min(val) < -1000.0:
                        val = np.zeros_like(
                            val
                        )  # Weird array, don't trust. Set everything to zeros.
                        print(
                            "Warning! Wind speed > 1000 m/s at "
                            + time.strftime("%Y-%m-%d %H:%M:%S")
                            + " !"
                        )
                        val[np.where(val == 0.0)] = np.nan
                if param == "barometric_pressure":
                    if np.max(val) > 200000.0:
                        val = np.zeros_like(
                            val
                        )  # Weird array, don't trust. Set everything to zeros.
                        val[np.where(val == 0.0)] = np.nan
                    if np.min(val) < 10000.0:
                        val = np.zeros_like(
                            val
                        )  # Weird array, don't trust. Set everything to zeros.
                        val[np.where(val == 0.0)] = np.nan
                if param == "precipitation":
                    if np.nanmax(val) > 1000.0:
                        val = np.zeros_like(
                            val
                        )  # Weird array, don't trust. Set everything to zeros.
                        print(
                            "Warning! Precipitation exceeds 1000 mm/h at "
                            + time.strftime("%Y-%m-%d %H:%M:%S")
                            + " !"
                        )
                        val[np.where(val == 0.0)] = np.nan
                    if np.nanmin(val) < 0.0:
                        val[np.where(val < 0.0)] = 0.0

                if np.all(np.isnan(val)):
                    if it > 0:
                        print(
                            "Warning! Only NaNs found for "
                            + param
                            + " at "
                            + time.strftime("%Y-%m-%d %H:%M:%S")
                            + " ! Using data from previous time."
                        )
                        val = val_previous
                    else:
                        if param == "wind" or param == "precipitation":
                            print(
                                "Warning! Only NaNs found for "
                                + param
                                + " at "
                                + time.strftime("%Y-%m-%d %H:%M:%S")
                                + " ! Setting values to 0.0 !"
                            )
                            val = np.zeros_like(val)
                        elif param == "barometric_pressure":
                            print(
                                "Warning! Only NaNs found for "
                                + param
                                + " at "
                                + time.strftime("%Y-%m-%d %H:%M:%S")
                                + " ! Setting values to 101300.0 !"
                            )
                            val = np.zeros_like(val) + 101300.0

                fid.write(
                    "TIME = "
                    + str(tim)
                    + " minutes since "
                    + refdate.strftime("%Y-%m-%d %H:%M:%S")
                    + " +00:00\n"
                )
                np.savetxt(fid, val, fmt=file["fmt"])

            # Add extra blocks if data does not cover time range
            if self.time[-1] < time_range[1]:
                dt = time_range[1] - refdate
                tim = dt.total_seconds() / 60
                val = np.flipud(file["data"][-1, :, :])
                # Skip blocks with only nans
                if not np.all(np.isnan(val)):
                    val[val == np.nan] = -999.0
                    fid.write(
                        "TIME = "
                        + str(tim)
                        + " minutes since "
                        + refdate.strftime("%Y-%m-%d %H:%M:%S")
                        + " +00:00\n"
                    )
                    np.savetxt(fid, val, fmt=file["fmt"])

            fid.close()

    def write_wind_to_json(self, file_name, time_range=None, iref=1, js=False):
        import json

        if not time_range:
            time_range = []
            time_range.append(self.time[0])
            time_range.append(self.time[-1])

        data = []

        header = {
            "discipline": 0,
            "disciplineName": "Meteorological products",
            "gribEdition": 2,
            "gribLength": 76420,
            "center": 7,
            "centerName": "US National Weather Service - NCEP(WMC)",
            "subcenter": 0,
            "refTime": "2016-04-30T06:00:00.000Z",
            "significanceOfRT": 1,
            "significanceOfRTName": "Start of forecast",
            "productStatus": 0,
            "productStatusName": "Operational products",
            "productType": 1,
            "productTypeName": "Forecast products",
            "productDefinitionTemplate": 0,
            "productDefinitionTemplateName": "Analysis/forecast at horizontal level/layer at a point in time",
            "parameterCategory": 2,
            "parameterCategoryName": "Momentum",
            "parameterNumber": 2,
            "parameterNumberName": "U-component_of_wind",
            "parameterUnit": "m.s-1",
            "genProcessType": 2,
            "genProcessTypeName": "Forecast",
            "forecastTime": 0,
            "surface1Type": 103,
            "surface1TypeName": "Specified height level above ground",
            "surface1Value": 10.0,
            "surface2Type": 255,
            "surface2TypeName": "Missing",
            "surface2Value": 0.0,
            "gridDefinitionTemplate": 0,
            "gridDefinitionTemplateName": "Latitude_Longitude",
            "numberPoints": 65160,
            "shape": 6,
            "shapeName": "Earth spherical with radius of 6,371,229.0 m",
            "gridUnits": "degrees",
            "resolution": 48,
            "winds": "true",
            "scanMode": 0,
            "nx": 360,
            "ny": 181,
            "basicAngle": 0,
            "subDivisions": 0,
            "lo1": 0.0,
            "la1": 90.0,
            "lo2": 359.0,
            "la2": -90.0,
            "dx": 1.0,
            "dy": 1.0,
        }

        header["lo1"] = float(min(self.x) + 360.0)
        header["lo2"] = float(max(self.x) + 360.0)
        header["la1"] = float(max(self.y))
        header["la2"] = float(min(self.y))
        header["dx"] = float(self.x[1] - self.x[0])
        header["dy"] = float(self.y[1] - self.y[0])
        header["nx"] = len(self.x)
        header["ny"] = len(self.y)
        header["numberPoints"] = len(self.x) * len(self.y)

        header_u = header.copy()
        header_v = header.copy()

        header_u["parameterNumberName"] = "U-component_of_wind"
        header_u["parameterNumber"] = 2
        header_v["parameterNumberName"] = "V-component_of_wind"
        header_v["parameterNumber"] = 3

        for it, t in enumerate(self.time):
            if t >= time_range[0] and t <= time_range[1]:
                dd = []

                tstr = t.strftime("%Y-%m-%dT%H:%M:%SZ")

                u_list = (
                    np.flipud(np.around(self.quantity[0].u[it, :, :], decimals=1))
                    .flatten()
                    .tolist()
                )
                data0 = {"header": header_u.copy(), "data": u_list}
                data0["header"]["refTime"] = tstr
                dd.append(data0)

                v_list = (
                    np.flipud(np.around(self.quantity[0].v[it, :, :], decimals=1))
                    .flatten()
                    .tolist()
                )
                data0 = {"header": header_v.copy(), "data": v_list}
                data0["header"]["refTime"] = tstr
                dd.append(data0)

                data.append(dd)

        json_string = json.dumps(data, separators=(",", ":"))
        fid = open(file_name, "w")
        if js:
            fid.write("wind = ")
        fid.write(json_string)
        fid.close()

    def write_to_netcdf(self, file_name):
        pass

    def subset(
        self,
        name=None,
        parameters=None,
        time_range=[],
        x=None,
        y=None,
        xlim=None,
        ylim=None,
        stride=1,
        tstride=1,
        crs=None,
        backup=None,
    ):
        if not time_range:
            times = self.time

        else:
            it0 = np.where(self.time == time_range[0])[0]
            if np.size(it0) == 0:
                # Find first available time
                it0 = np.where(
                    (self.time >= time_range[0]) * (self.time <= time_range[1])
                )[0]
                if np.size(it0) == 0:
                    print("No data found in requested time range.")
                    dataset = []
                    return dataset
                else:
                    it0 = it0[0]
                    print("First requested time not found. Using first time available.")

            else:
                it0 = it0[0]

            it1 = np.where(self.time == time_range[1])[0]
            if np.size(it1) == 0:
                # Find last available time
                it1 = np.where(
                    (self.time >= time_range[0]) * (self.time <= time_range[1])
                )[0]
                if np.size(it1) == 0:
                    print("No data found in requested time range.")
                    dataset = []
                    return dataset
                else:
                    it1 = it1[-1]
                    print("Last requested time not found. Using last time available.")
            else:
                it1 = it1[0]

            times = self.time[it0 : it1 + 1]

        interp = False
        if x is not None and y is not None:
            # Re-interpolate
            xg, yg = np.meshgrid(x, y)
            interp = True
        elif xlim is not None and ylim is not None:
            # Limit based on bbox
            np.where(self.x >= xlim[1])[-1]
            j0 = np.asarray(np.where(self.x <= xlim[0]))[0][-1]
            j1 = np.asarray(np.where(self.x >= xlim[1]))[0][0] + 1
            i0 = np.asarray(np.where(self.y <= ylim[0]))[0][-1]
            i1 = np.asarray(np.where(self.y >= ylim[1]))[0][0] + 1
            x = self.x[j0:j1:stride]
            y = self.y[i0:i1:stride]
        else:
            j0 = 0
            j1 = len(self.x) - 1
            i0 = 0
            i1 = len(self.y) - 1
            x = self.x[j0:j1:stride]
            y = self.y[i0:i1:stride]

        if not crs:
            crs = self.crs
        else:
            if interp:
                transformer = Transformer.from_crs(crs, self.crs, always_xy=True)
                xg, yg = transformer.transform(xg, yg)

        # Make a new dataset
        dataset = MeteoGrid()

        dataset.time = times
        dataset.x = x
        dataset.y = y
        dataset.crs = crs
        dataset.last_analysis_time = self.last_analysis_time

        nrows = len(y)
        ncols = len(x)
        nt = len(times)

        for q in self.quantity:
            if q.name == "wind":
                q1 = MeteoMatrixVector()
                q1.u = np.zeros((nt, nrows, ncols))
                q1.v = np.zeros((nt, nrows, ncols))
            else:
                q1 = MeteoMatrixScalar()
                q1.val = np.zeros((nt, nrows, ncols))

            q1.name = q.name
            q1.unit = q.unit

            for it, time in enumerate(times):
                it0 = int(np.where(self.time == time)[0])

                if interp:
                    if q.name == "wind":
                        q1.u[it, :, :] = interp2(self.x, self.y, q.u[it0, :, :], xg, yg)
                        q1.v[it, :, :] = interp2(self.x, self.y, q.v[it0, :, :], xg, yg)
                    else:
                        q1.val[it, :, :] = interp2(
                            self.x, self.y, q.val[it0, :, :], xg, yg
                        )

                else:
                    if q.name == "wind":
                        q1.u[it, :, :] = q.u[it0, i0:i1:stride, j0:j1:stride]
                        q1.v[it, :, :] = q.v[it0, i0:i1:stride, j0:j1:stride]
                    else:
                        q1.val[it, :, :] = q.val[it0, i0:i1:stride, j0:j1:stride]

            dataset.quantity.append(q1)

        return dataset

    def to_pandas(self):
        pass

    def find_cyclone_tracks(
        self, xlim=[-1.0e9, 1.0e9], ylim=[-1.0e9, 1.0e9], pcyc=99000.0, dist=2.0, dt=6
    ):
        tstride = np.round(dt / self.source.time_interval).astype(int)

        tracks = []

        nt = np.size(self.time)

        for it in range(0, nt, tstride):
            #        for it, time in enumerate(self.time[::tstride]):

            x = self.x
            y = self.y
            time = self.time[it]
            u = np.squeeze(self.quantity[0].u[it, :, :])
            v = np.squeeze(self.quantity[0].v[it, :, :])
            p = np.squeeze(self.quantity[1].val[it, :, :])

            xeye, yeye, vmax, peye = find_cyclone_eyes(
                x, y, u, v, p, pcyc, dist, xlim, ylim
            )

            # Check if these locations match with previous tracks
            for j in range(len(xeye)):
                itrack = -1
                for k, track in enumerate(tracks):
                    coords = track.track.geometry
                    ids_coords = track.track.geometry.size
                    dst = np.sqrt(
                        (coords[ids_coords - 1].x - xeye[j]) ** 2
                        + (coords[ids_coords - 1].y - yeye[j]) ** 2
                    )
                    if dst < dist:
                        itrack = k

                # Define time point
                # We assume winds are in m/s and 1-minute averaged!!!!
                point = Point(xeye[j], yeye[j])
                tc_time_string = time.strftime(date_format)
                gdf = gpd.GeoDataFrame(
                    {
                        "datetime": tc_time_string,
                        "geometry": [point],
                        "vmax": [vmax[j] / 0.514444],
                        "pc": [peye[j]],
                        "RMW": [-999],
                        "R35_NE": [-999],
                        "R35_SE": [-999],
                        "R35_SW": [-999],
                        "R35_NW": [-999],
                        "R50_NE": [-999],
                        "R50_SE": [-999],
                        "R50_SW": [-999],
                        "R50_NW": [-999],
                        "R65_NE": [-999],
                        "R65_SE": [-999],
                        "R65_SW": [-999],
                        "R65_NW": [-999],
                        "R100_NE": [-999],
                        "R100_SE": [-999],
                        "R100_SW": [-999],
                        "R100_NW": [-999],
                    }
                )
                gdf = gdf.set_crs(epsg=4326)

                # Is this a new track or append it?
                if itrack >= 0:
                    # Existing track - append tracks
                    tracks[itrack].track = pd.concat([tracks[itrack].track, gdf])
                    tracks[itrack].track = tracks[itrack].track.reset_index(drop=True)

                else:
                    # Make new track
                    track_name = "new_track" + str(len(tracks))
                    new_track = TropicalCyclone(name=track_name)
                    tracks.append(new_track)

                    # Append point
                    tracks[-1].track = pd.concat([tracks[-1].track, gdf])
                    tracks[-1].track = tracks[-1].track.reset_index(drop=True)
                    tracks[-1].track = tracks[-1].track.drop([0])  # remove the dummy
                    tracks[-1].track = tracks[-1].track.reset_index(drop=True)

        # return tracks
        return tracks


def merge(forcing_list):
    meteo_grid = MeteoGrid()

    return meteo_grid


class CycloneTrack:
    def __init__(self, time=None, lon=None, lat=None, vmax=None, pc=None):
        if not time:
            time = []
        if not lon:
            lon = []
        if not lat:
            lat = []
        if not vmax:
            vmax = []
        if not pc:
            pc = []

        self.time = time
        self.lon = lon
        self.lat = lat
        self.vmax = vmax
        self.pc = pc


class MeteoSpiderweb:
    def __init__(
        self,
        name=None,
        parameters=None,
        path=None,
        long_name=None,
        spw_radius=None,
        crs=None,
        filename=None,
    ):
        self.name = name
        self.crs = crs
        if not long_name:
            self.long_name = name
        else:
            self.long_name = long_name

        self.path = path
        self.time = None
        self.spw_radius = None
        self.spw_rad_unit = None
        self.x_spw_eye = None
        self.y_spw_eye = None
        self.p_drop_spw_eye = None
        self.quantity = {}

        if filename:
            self.read(filename)

    def read(self, file_name, format="delft3d"):
        spw = None
        if format == "delft3d":
            spw = read_delft3d_spiderweb_file(file_name)
        return spw

    def write(self, file_name, format="delft3d"):
        pass
        # if format == "delft3d":
        #     write_delft3d_spiderweb_file(file_name)

    def to_meteo_grid(
        self,
        meteogrid=None,
        x_range=None,
        y_range=None,
        dx=None,
        dy=None,
        filename=None,
        crs=None,
        gapres=101300.0,
        time_range=None,
    ):
        meteo_grid = None

        if not time_range:
            time_range = [self.time[0], self.time[-1]]

        if meteogrid:
            pass
        elif x_range is not None and y_range is not None:
            meteogrid = MeteoGrid(
                x_range=x_range, y_range=y_range, dx=dx, dy=dy, crs=self.crs
            )
            meteogrid.quantity["wind_u"] = {}
            meteogrid.quantity["wind_v"] = {}
            meteogrid.quantity["barometric_pressure"] = {}
        else:
            print("Error! Either a MeteoGrid or x and y coordinates must be supplied!")
            return meteo_grid

        # size = self.quantity["wind_speed"]["data"]
        # nrows = size[1]
        # ncols = size[2]

        nt0 = len(self.time)  # original track length

        nt = 0
        it0 = None
        it1 = None
        for it in range(nt0):
            if self.time[it] >= time_range[0] and self.time[it] <= time_range[1]:
                nt += 1
                if it0 is None:
                    it0 = it
                it1 = it

        # Make regular mesh
        x = meteogrid.x
        y = meteogrid.y

        xg, yg = np.meshgrid(meteogrid.x, meteogrid.y)

        # Initialize arrays
        dtp = np.dtype("object")
        meteogrid.time = np.empty((nt), dtype=dtp)
        meteogrid.quantity["wind_u"]["data"] = np.empty((nt, len(y), len(x)))
        meteogrid.quantity["wind_v"]["data"] = np.empty((nt, len(y), len(x)))
        meteogrid.quantity["barometric_pressure"]["data"] = np.empty(
            (nt, len(y), len(x))
        )
        #        meteogrd.quantity["precipitation"]["data"]   = np.array((nt,len(y),len(x)))
        frac = np.empty((nt, len(y), len(x)))

        # Loop through time steps
        j = -1
        for it in range(it0, it1 + 1):
            j += 1

            xe = self.x_spw_eye[it]
            ye = self.y_spw_eye[it]
            radius = self.spw_radius
            # dxg = (xg - xe)*111111*np.cos(ye*np.pi)
            # dyg = (yg - ye)*111111
            # dst = np.sqrt(np.square(dxg) + np.square(dyg))
            # phi = np.atan2(dyg, dxg)

            umag = np.squeeze(self.quantity["wind_speed"]["data"][it, :, :])
            udir = np.squeeze(self.quantity["wind_from_direction"]["data"][it, :, :])
            udir = 1.5 * np.pi - np.pi * udir / 180  # wind speed to (cartesian)
            uspw = umag * np.cos(udir)
            vspw = umag * np.sin(udir)
            pspw = gapres - np.squeeze(self.quantity["p_drop"]["data"][it, :, :])

            ugrd, frac = radial2regular(xg, yg, xe, ye, radius, uspw)
            vgrd, frac = radial2regular(xg, yg, xe, ye, radius, vspw)
            pgrd, frac = radial2regular(xg, yg, xe, ye, radius, pspw)

            ugrd[np.isnan(ugrd)] = 0.0
            vgrd[np.isnan(vgrd)] = 0.0
            pgrd[np.isnan(pgrd)] = gapres

            meteogrid.quantity["wind_u"]["data"][j, :, :] = ugrd * frac
            meteogrid.quantity["wind_v"]["data"][j, :, :] = vgrd * frac
            meteogrid.quantity["barometric_pressure"]["data"][j, :, :] = pgrd

            meteogrid.time[j] = self.time[it]

        return meteogrid

    def resample(self, time_range=None, dt=None):
        if not time_range:
            time_range = [self.time[0], self.time[-1]]

        t = pd.date_range(
            start=time_range[0], end=time_range[1], freq=pd.DateOffset(seconds=dt)
        ).to_pydatetime()

        t0 = [tt.timestamp() for tt in self.time]
        t1 = [tt.timestamp() for tt in t]

        x0 = self.x_spw_eye
        y0 = self.y_spw_eye
        x1 = np.interp(t1, t0, x0)
        y1 = np.interp(t1, t0, y0)

        vmag = self.quantity["wind_speed"]["data"]
        vdir = self.quantity["wind_from_direction"]["data"]
        vdir = 1.5 * np.pi - vdir * np.pi / 180
        u0 = vmag * np.cos(vdir)
        v0 = vmag * np.sin(vdir)

        f = interpolate.interp1d(t0, u0, axis=0)
        u1 = f(t1)
        f = interpolate.interp1d(t0, v0, axis=0)
        v1 = f(t1)
        f = interpolate.interp1d(t0, self.quantity["p_drop"]["data"], axis=0)
        p = f(t1)

        vmag = np.sqrt(u1 * u1 + v1 * v1)
        vdir = np.arctan2(v1, u1)
        vdir = 270.0 - vdir * 180 / np.pi

        self.time = t
        self.x_spw_eye = x1
        self.y_spw_eye = y1
        self.quantity["wind_speed"]["data"] = vmag
        self.quantity["wind_from_direction"]["data"] = vdir
        self.quantity["p_drop"]["data"] = p

    def from_meteo_grid(self, meteo_grid, crs=None):
        pass


def radial2regular(
    xg,
    yg,
    xp,
    yp,
    radius,
    val,
    merge_frac=0.5,
    projection="geographic",
    convention="nautical",
):
    # Dimensions and sizes of input data
    sz = np.shape(val)
    nrad = sz[0]
    ndir = sz[1]
    dx = radius / nrad
    dphi = 360.0 / ndir

    # Compute distances (in metres) and angles for each point in local grid
    if projection == "geographic":
        cfacx = 111111 * np.cos(np.pi * yp / 180)
        cfacy = 111111.0
    else:
        cfacx = 1.0
        cfacy = 1.0

    dxg = (xg - xp) * cfacx
    dyg = (yg - yp) * cfacy

    dst = np.sqrt(np.square(dxg) + np.square(dyg))
    ang = np.arctan2(dyg, dxg)

    if convention == "nautical":
        ang = np.pi / 2 - ang

    ang = np.mod(ang, 2 * np.pi)
    ang = ang * 180 / np.pi

    # Spatial merge function
    fm0 = 1.0 / (1.0 - merge_frac)
    fm = fm0 * dst / radius - fm0 + 1.0
    frac = np.maximum(0.0, np.minimum(1.0, fm))
    frac = 1.0 - frac

    # Take average value of surrounding spiderweb points
    #
    #         i     i
    #         d     d
    #         i     i
    #         r     r
    #         2     1
    #
    #  ^    3 o-----o 4  irad2
    #  |      |     |
    #  r      |     |
    #  a      |     |
    #  d    2 o-----o 1  irad1
    #
    #         <- idir

    # Radial index
    irad1 = (np.floor(dst / dx) - 1).astype(int)
    # Relative distance (0-1) between radial points
    drad = dst / dx - (irad1 + 1).astype(float)
    irad2 = irad1 + 1
    # Points that are very close to the eye
    irad1[np.where(irad1 == -1)] = 0
    # Points that are outside of the radius
    iout = np.where(irad2 > nrad - 1)
    irad1[np.where(irad2 > nrad - 1)] = 0
    irad2[np.where(irad2 > nrad - 1)] = 0

    # Directional index
    idir1 = (np.floor(ang / dphi)).astype(int)
    # Relative distance (0-1) between directional points
    ddir = ang / dphi - idir1.astype(float)
    idir2 = idir1 + 1
    idir1[np.where(idir2 > ndir - 1)] = 0
    idir2[np.where(idir2 > ndir - 1)] = 1

    # Compute weights of surrounding spiderweb points
    f1 = (1.0 - ddir) * (1.0 - drad)
    f2 = (ddir) * (1.0 - drad)
    f3 = (ddir) * (drad)
    f4 = (1.0 - ddir) * (drad)

    zg = f1 * val[irad1, idir1]
    zg = zg + f2 * val[irad1, idir2]
    zg = zg + f3 * val[irad2, idir2]
    zg = zg + f4 * val[irad2, idir1]

    zg[iout] = np.nan

    return zg, frac


def find_cyclone_eyes(x, y, u, v, p, pcyc, mindist, xlim, ylim):
    # Return lists with cyclone x, y, vmax, pc
    xeye = []
    yeye = []
    vmax = []
    pc = []

    xx, yy = np.meshgrid(x, y)

    vmag = np.sqrt(u**2 + v**2)

    ibelow = np.where(p < pcyc)
    xb = xx[ibelow]
    yb = yy[ibelow]

    iin = np.where(
        (xb >= xlim[0]) & (xb <= xlim[1]) & (yb >= ylim[0]) & (yb <= ylim[1])
    )
    xb = xb[iin]
    yb = yb[iin]

    dx = x[1] - x[0]
    ng = round(2 * mindist / dx)

    if np.size(xb) > 0:
        clusters = find_clusters(xb, yb, mindist)

        for k, cluster in enumerate(clusters):
            # Centre of the cluster
            xc = cluster.x
            yc = cluster.y

            # Grid indices
            ix = np.where(x > xc)[0][0]
            iy = np.where(y > yc)[0][0]

            i0 = max(iy - ng, 0)
            i1 = min(iy + ng, np.size(y) - 1)
            j0 = max(ix - ng, 0)
            j1 = min(ix + ng, np.size(x) - 1)

            xxx = x[j0:j1]
            yyy = y[i0:i1]

            zzz = p[i0:i1, j0:j1]

            xxxf = np.arange(x[j0], x[j1], dx / 5)
            yyyf = np.arange(y[i0], y[i1], dx / 5)
            #        xxxf, yyyf = np.meshgrid(xxxf,yyyf)
            #        try:
            F = interpolate.RectBivariateSpline(xxx, yyy, np.transpose(zzz))
            #        except:
            #            shite=1
            zzzf = F(xxxf, yyyf)
            i, j = np.where(zzzf == np.min(zzzf))
            i = i[0]
            j = j[0]
            xeye.append(xxxf[i])
            yeye.append(yyyf[j])

            vmg = vmag[i0:i1, j0:j1]
            prs = p[i0:i1, j0:j1]

            vmax.append(np.max(vmg))
            pc.append(np.min(prs))

    return xeye, yeye, vmax, pc


def find_clusters(x, y, dmin):
    clusters = []

    n = np.size(x)
    icluster = np.zeros(n).astype(int) - 1

    for j in range(n):
        xp = x[j]
        yp = y[j]
        dst = np.sqrt((x - xp) ** 2 + (y - yp) ** 2)
        inear = np.where(dst < dmin)
        if not np.any(inear):
            # Starting a new cluster
            icluster[j] = np.max(icluster) + 1
        else:
            nearcluster = icluster[inear]
            nearcluster = nearcluster[np.where(nearcluster >= 0)]
            # nearcluster contains all the points that are nearby and are already in a cluster
            if np.size(nearcluster) == 0:
                # Must be j==1
                newcluster = np.max(icluster) + 1
                icluster[j] = newcluster
                nearcluster = newcluster
            kmin = np.min(nearcluster)
            if icluster[j] >= 0:
                icluster[np.where(icluster == icluster[j])] = kmin
            icluster[inear] = kmin

    nclusters = np.max(icluster) + 1

    for j in range(nclusters):
        k = np.where(icluster == j)
        cluster = Cluster()
        cluster.index = k
        cluster.x = np.mean(x[k])
        cluster.y = np.mean(y[k])
        clusters.append(cluster)

    return clusters


class Cluster:
    def __init__(self):
        self.x = None
        self.y = None
        self.index = None
