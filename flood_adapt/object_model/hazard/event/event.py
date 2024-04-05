import glob
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Self, Union

import cht_observations.observation_stations as cht_station
import hydromt.raster  # noqa: F401
import numpy as np
import pandas as pd
import pyproj
import tomli
import tomli_w
import xarray as xr
from cht_cyclones.tropical_cyclone import TropicalCyclone
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS
from shapely.affinity import translate

from flood_adapt.object_model.interface.events import (
    DEFAULT_DATETIME_FORMAT,
    DEFAULT_TIMESTEP,
    EventModel,
    IEvent,
    Mode,
    RainfallSource,
    SurgeSource,
    TideSource,
    WindSource,
)
from flood_adapt.object_model.interface.site import ISite, RiverModel
from flood_adapt.object_model.io.timeseries import Timeseries
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitfulTime,
    UnitTypesLength,
    UnitTypesTime,
)
from flood_adapt.object_model.site import Site


class Event(IEvent):
    """
    Event class that is described by a validated EventModel.

    Attributes
    ----------
    attrs : EventModel
        - name: Required[str]
        - description: Optional[str]
        - mode: Required[Mode]
        - time: Required[TimeModel]
        - overland: Optional[OverlandModel]
        - offshore: Optional[OffshoreModel]

    Methods
    -------
    save(filepath: Union[str, os.PathLike])
        Save the event to a toml file.
    load_file(filepath: Union[str, os.PathLike])
        Load the event from a toml file.
    load_dict(data: dict[str, Any])
        Load the event from a dictionary.
    get_mode(filepath: Path) -> Mode
        Get the mode of the event from a toml file.
    add_river_discharge_ts(event_dir: Path, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self
        Compute timeseries of the event generated from the combination of timing model and river discharge models.
    add_rainfall_ts(time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self
        Compute timeseries of the event generated from the combination of timing model and rainfall model.
    add_overland_wind_ts(time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self
        Compute timeseries of the event generated from the combination of timing model and overland wind model.
    add_offshore_wind_ts(time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self
        Compute timeseries of the event generated from the combination of timing model and offshore wind model
    add_tide_and_surge_ts(time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self
        Compute timeseries of the event generated from the combination of timing model, tide model and surge model.
    download_wl_data(station_id: int, start_time_str: str, stop_time_str: str, units: UnitTypesLength) -> pd.DataFrame
        Download water level data from NOAA station using station_id, start and stop time.
    download_meteo(site: ISite, path: Path)
        Download meteo data from GFS for the event location.
    make_spw_file(database_path: Path, model_dir: Path, site=Site)
        Create a spiderweb file from the hurricane track.
    translate_tc_track(tc: TropicalCyclone, site: Site)
        Translate the hurricane track in the local coordinate system.
    """

    def save(self, filepath: Union[str, os.PathLike]):
        """saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.model_dump(exclude_none=True), f)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Projection from toml file"""
        obj = Event()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = EventModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Projection from object, e.g. when initialized from GUI"""
        obj = Event()
        obj.attrs = EventModel.model_validate(data)
        return obj

    @staticmethod
    def get_mode(filepath: Path) -> Mode:
        """get mode of the event (single or risk) from toml file"""

        with open(filepath, mode="rb") as fp:
            event_data = tomli.load(fp)
        mode = event_data["mode"]
        if not isinstance(mode, Mode):
            raise ValueError(f"Unsupported mode: {mode}.")
        return mode

    def add_river_discharge_ts(
        self,
        event_dir: Path,
        site_river: list[RiverModel] = None,
        time_step: UnitfulTime = DEFAULT_TIMESTEP,
    ) -> Self:
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  List of River Discharge Models:
            determines the timeframe (start & end) of the river discharge timeseries within the event, and the intensity of the discharge

        Parameters
        ----------
        event_dir : Path
            Path to the directory where the river discharge timeseries are stored
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The river discharge timeseries is stored in the self.dis_df attribute, in pd.DataFrame format with time as index and each river discharge as a column.
        """
        if site_river is None:
            self.dis_df = None
            return self

        # Create empty list for results
        list_df = []
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        for ii, rivermodel in enumerate(site_river):
            rivermodel = rivermodel.model_copy(deep=True)
            rivermodel.timeseries.start_time = (
                event_start + rivermodel.timeseries.start_time.to_timedelta()
            )
            rivermodel.timeseries.end_time = (
                event_start + rivermodel.timeseries.end_time.to_timedelta()
            )
            rivermodel.timeseries.peak_intensity = (
                rivermodel.timeseries.peak_intensity - rivermodel.base_discharge
            )
            rivermodel.timeseries.csv_file_path = (
                event_dir / rivermodel.timeseries.csv_file_path
            )

            discharge = Timeseries.load_dict(rivermodel.timeseries).to_dataframe(
                start_time=event_start, end_time=event_end, time_step=time_step
            )
            discharge += rivermodel.base_discharge.value
            list_df[ii] = discharge

            # Concatenate dataframes and add to event class
            self.dis_df = (
                pd.concat(list_df, axis=1, join="outer")
                .interpolate(method="time")  # interpolate missing values in between
                .fillna(method="ffill")  # fill missing values at the beginning
                .fillna(method="bfill")  # fill missing values at the end
            )
        return self

    def add_rainfall_ts(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self:
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  Timeseries model:
            determines the timeframe (start & end) of the rainfall timeseries within the event, and the intensity of the rainfall

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The rainfall timeseries is stored in the self.rainfall_ts attribute, in pd.DataFrame format with time as index and intensity as first column.
        """
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        rainfall_model = self.attrs.overland.rainfall
        if rainfall_model.source == RainfallSource.timeseries:
            event_rainfall_df = Timeseries.load_dict(
                rainfall_model.timeseries
            ).to_dataframe(
                start_time=event_start, end_time=event_end, time_step=time_step
            )
            self.rainfall_ts = event_rainfall_df
        else:  # track, map, none
            raise ValueError(f"Unsupported rainfall source: {rainfall_model.source}.")
        return self

    def add_overland_wind_ts(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self:
        """Adds constant wind or timeseries from overlandModel to event object.

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        Self
            Updated object with wind timeseries added to self.overland_wind_ts in pd.DataFrame format with time as index,
            the magnitude of the wind speed as first column and the direction as second column.
        """
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        tstop = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_vec = pd.date_range(
            tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
        )
        if self.attrs.overland.wind.source == WindSource.constant:
            vmag = self.attrs.overland.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.overland.wind.constant_direction.value * np.array([1, 1])
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )

        elif self.attrs.overland.wind.source == WindSource.timeseries:
            wind_df = Timeseries.read_csv(self.attrs.overland.wind.timeseries_file)
            df = pd.DataFrame.from_dict(
                {
                    "time": time_vec[[0, -1]],
                    "vmag": wind_df["vmag"],
                    "vdir": wind_df["vdir"],
                }
            )
        else:  # track, map, none
            raise ValueError(
                f"Unsupported wind source: {self.attrs.overland.wind.source}."
            )

        df = df.set_index("time")
        self.overland_wind_ts = df
        return self

    def add_offshore_wind_ts(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self:
        """Adds constant wind or timeseries from offshoreModel to event object.

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step for generating the time series of constant wind, by default 600 seconds

        Returns
        -------
        self
            Updated object with wind timeseries added to self.offshore_wind_ts in pd.DataFrame format with time as index,
            the magnitude of the wind speed as first column and the direction as second column.
        """
        tstart = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        tstop = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        duration = (tstop - tstart).total_seconds()
        time_step = int(time_step)
        time_vec = pd.date_range(
            tstart, periods=duration / time_step + 1, freq=f"{time_step}S"
        )
        if self.attrs.offshore.wind.source == WindSource.constant:
            vmag = self.attrs.offshore.wind.constant_speed.value * np.array([1, 1])
            vdir = self.attrs.offshore.wind.constant_direction.value * np.array([1, 1])
            df = pd.DataFrame.from_dict(
                {"time": time_vec[[0, -1]], "vmag": vmag, "vdir": vdir}
            )

        elif self.attrs.offshore.wind.source == WindSource.timeseries:
            wind_df = Timeseries.read_csv(self.attrs.offshore.wind.timeseries_file)
            df = pd.DataFrame.from_dict(
                {
                    "time": time_vec[[0, -1]],
                    "vmag": wind_df["vmag"],
                    "vdir": wind_df["vdir"],
                }
            )
        else:  # track, map, none
            raise ValueError(
                f"Unsupported wind source: {self.attrs.offshore.wind.source}."
            )

        df = df.set_index("time")
        self.offshore_wind_ts = df
        return self

    def add_tide_and_surge_ts(self, time_step: UnitfulTime = DEFAULT_TIMESTEP) -> Self:
        """
        Compute timeseries of the event generated from the combination of:
        1.  Timing Model:
            determines the total duration of the event and has default values of 0 for the whole duration of the event
        2.  TideModel:
            determines the timeframe (start, end & phase) of the tide timeseries within the event, and the harmonic amplitude of the tide
        3.  SurgeModel:
            determines the timeframe (start & end) of the surge timeseries within the event, and the intensity of the surge

        Parameters
        ----------
        time_step : UnitfulTime, optional
            Time step of the generated time series, by default 600 seconds

        Returns
        -------
        Self
            The tide and surge timeseries is stored in the self.tide_surge_ts attribute, in pd.DataFrame format with time as index and intensity as first column.
        """
        event_start = datetime.strptime(
            self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT
        )
        event_end = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)

        surge_model = self.attrs.overland.surge
        if surge_model is not None:
            if surge_model.source == SurgeSource.timeseries:
                event_surge_df = Timeseries.load_dict(
                    surge_model.timeseries
                ).to_dataframe(
                    start_time=event_start, end_time=event_end, time_step=time_step
                )
            else:  # track, map, none
                raise ValueError(f"Unsupported surge source: {surge_model.source}.")

        tide_model = self.attrs.overland.tide
        if tide_model is not None:
            if tide_model.source == TideSource.timeseries:
                tide_model.timeseries.start_time = UnitfulTime(
                    0, UnitTypesTime.seconds
                )  # tide is always oscillating
                tide_model.timeseries.end_time = UnitfulTime(
                    event_end.timestamp(), UnitTypesTime.seconds
                )
                event_tide_df = Timeseries.load_dict(
                    tide_model.timeseries
                ).to_dataframe(
                    start_time=event_start, end_time=event_end, time_step=time_step
                )
            else:  # track, map, none
                raise ValueError(f"Unsupported tide source: {tide_model.source}.")

        # Add final tide and surge timeseries to event if specified
        if event_surge_df is None:
            self.tide_surge_ts = event_tide_df
        elif event_tide_df is None:
            self.tide_surge_ts = event_surge_df
        else:
            self.tide_surge_ts = event_surge_df.add(
                event_tide_df, axis="index", fill_value=0
            )

        return self

    @staticmethod
    def download_wl_data(
        station_id: int, start_time_str: str, stop_time_str: str, units: UnitTypesLength
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        station_id : int
            NOAA observation station ID.
        start_time_str : str
            Start time of timeseries in the form of: "YYYMMDD HHMMSS"
        stop_time_str : str
            End time of timeseries in the form of: "YYYMMDD HHMMSS"

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        start_time = datetime.strptime(start_time_str, "%Y%m%d %H%M%S")
        stop_time = datetime.strptime(stop_time_str, "%Y%m%d %H%M%S")
        # Get NOAA data
        source = cht_station.source("noaa_coops")
        df = source.get_data(station_id, start_time, stop_time)
        df = pd.DataFrame(df)  # Convert series to dataframe
        df = df.rename(columns={"v": 1})
        conversion_factor = (
            UnitfulLength(1.0, UnitTypesLength.meters).convert(units).value
        )
        df = conversion_factor * df
        return df

    def download_meteo(self, site: ISite, path: Path):
        logging.info("Downloading meteo data...")
        params = ["wind", "barometric_pressure", "precipitation"]
        lon = site.attrs.lon
        lat = site.attrs.lat

        # Download the actual datasets
        gfs_source = MeteoSource(
            "gfs_anl_0p50", "gfs_anl_0p50_04", "hindcast", delay=None
        )

        # Create subset
        name = "gfs_anl_0p50_us_southeast"
        gfs_conus = MeteoGrid(
            name=name,
            source=gfs_source,
            parameters=params,
            path=path,
            x_range=[lon - 10, lon + 10],
            y_range=[lat - 10, lat + 10],
            crs=CRS.from_epsg(4326),
        )

        # Download and collect data
        t0 = datetime.strptime(self.attrs.time.start_time, DEFAULT_DATETIME_FORMAT)
        t1 = datetime.strptime(self.attrs.time.end_time, DEFAULT_DATETIME_FORMAT)
        time_range = [t0, t1]

        gfs_conus.download(time_range)

        datasets = []
        for filename in sorted(glob.glob(str(path.joinpath("*.nc")))):
            # Open the file as an xarray dataset
            ds = xr.open_dataset(filename)

            # Extract the timestring from the filename and convert to pandas datetime format
            time_str = filename.split(".")[-2]
            time = pd.to_datetime(
                time_str, format=DEFAULT_DATETIME_FORMAT.replace(" ", "_")
            )

            # Add the time coordinate to the dataset
            ds["time"] = time

            # Append the dataset to the list
            datasets.append(ds)

        # Concatenate the datasets along the new time coordinate
        ds = xr.concat(datasets, dim="time")
        ds.raster.set_crs(4326)

        return ds

    def make_spw_file(self, database_path: Path, model_dir: Path, site=Site):
        # Location of tropical cyclone database
        cyc_file = database_path.joinpath(
            "input",
            "events",
            f"{self.attrs.name}",
            f"{self.attrs.hurricane.track_name}.cyc",
        )
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane.hurricane_translation.northsouth_translation.value
            != 0
        ):
            tc = self.translate_tc_track(tc=tc, site=site)

        # Location of spw file
        filename = "hurricane.spw"
        spw_file = model_dir.joinpath(filename)
        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

    def translate_tc_track(self, tc: TropicalCyclone, site: Site):
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(site.attrs.sfincs.csname)
        tc.track = tc.track.to_crs(crs)

        # Translate the track in the local coordinate system
        tc.track["geometry"] = tc.track["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=self.attrs.hurricane.hurricane_translation.eastwest_translation.convert(
                    UnitTypesLength.meters
                ).value,
                yoff=self.attrs.hurricane.hurricane_translation.northsouth_translation.convert(
                    UnitTypesLength.meters
                ).value,
            )
        )

        # Convert the geodataframe to lat/lon
        tc.track = tc.track.to_crs(epsg=4326)
        return tc

    def __eq__(self, other):
        if not isinstance(other, Event):
            # don't attempt to compare against unrelated types
            raise NotImplementedError
        attrs_1, attrs_2 = self.attrs.model_copy(), other.attrs.model_copy()
        attrs_1.__delattr__("name"), attrs_2.__delattr__("name")
        attrs_1.__delattr__("description"), attrs_2.__delattr__("description")
        return attrs_1 == attrs_2
