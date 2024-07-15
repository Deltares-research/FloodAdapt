import glob
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List

import cht_observations.observation_stations as cht_station
import pandas as pd
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS

# Maybe the way to stop circular imports is to import the database like this instead of importing the class directly
import flood_adapt.dbs_controller as db
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.interface.events import (
    IEvent,
    IEventModel,
    Mode,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IWaterlevel,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite, Obs_pointModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength


class HistoricalEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalNearshore that extend the parent class Event."""

    ALLOWED_FORCINGS: dict[ForcingType, List[ForcingSource]] = {
        ForcingType.RAINFALL: [ForcingSource.CONSTANT, ForcingSource.MODEL],
        ForcingType.WIND: [ForcingSource.CONSTANT, ForcingSource.MODEL],
        ForcingType.WATERLEVEL: [ForcingSource.CSV, ForcingSource.MODEL],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT],
    }


class HistoricalEvent(IEvent):
    MODEL_TYPE = HistoricalEventModel

    attrs: HistoricalEventModel

    def __init__(self):
        self._site: ISite = db.Database().site
        self._logger = FloodAdaptLogging().getLogger(__name__)

    def process(self, scenario: IScenario):
        """Preprocess, run and postprocess offshore model to obtain water levels for boundary condition of the overland model."""
        self._scenario = scenario

        if self.attrs.mode == Mode.risk:
            self._process_risk_event(scenario)
        else:
            self._process_single_event(scenario)

    def _process_risk_event(self, scenario: IScenario):
        # TODO implement / make a separate class for risk events
        pass

    def _process_single_event(self, scenario: IScenario):
        if self._site.attrs.sfincs.offshore_model is None:
            raise ValueError(
                f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.__class__.__name__}'"
            )
        sim_path = self._get_simulation_path()
        self._logger.info("Collecting forcing data ...")

        for forcing in self.attrs.forcings.values():
            if forcing is not None:
                if isinstance(forcing, (WaterlevelFromModel)):
                    self._preprocess_sfincs_offshore(sim_path, forcing)
                    self._run_sfincs_offshore(sim_path)
                    forcing.path = sim_path
                elif isinstance(forcing, WaterlevelFromGauged):
                    out_path = sim_path / "waterlevels.csv"
                    self._get_observed_wl_data(out_path=out_path)
                    forcing.path = out_path

                self.forcing_data[forcing._type] = forcing.get_data()

    def _preprocess_sfincs_offshore(
        self, sim_path: str | os.PathLike, forcing: IWaterlevel
    ):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        Args:
            ds (xr.DataArray): DataArray with meteo information (downloaded using event._download_meteo())
        """
        self._logger.info("Preparing offshore model to generate water levels...")

        if forcing._source == ForcingSource.MODEL:
            # Download meteo data
            meteo_dir = db.Database().output_path.joinpath("meteo")
            if not meteo_dir.is_dir():
                os.mkdir(db.Database().output_path.joinpath("meteo"))

            self._download_meteo(site=self._site, path=meteo_dir)
            ds = self._read_meteo(meteo_dir)
        else:
            ds = None

        # Initialize
        if os.path.exists(sim_path):
            shutil.rmtree(sim_path)
        os.makedirs(sim_path, exist_ok=True)

        template_offshore = db.Database().static_path.joinpath(
            "templates", self._site.attrs.sfincs.offshore_model
        )
        with SfincsAdapter(model_root=template_offshore) as _offshore_model:
            # Edit offshore model
            _offshore_model.set_timing(self.attrs)

            # Add water levels
            physical_projection = (
                db.Database()
                .projections.get(self._scenario.attrs.projection)
                .get_physical_projection()
            )
            _offshore_model._add_bzs_from_bca(self.attrs, physical_projection)

            # Add wind and if applicable pressure forcing from meteo data
            # TODO make it easier to access and change forcings
            wind_forcing = self.attrs.forcings[ForcingType.WIND]
            if wind_forcing is not None:
                # Add wind forcing
                _offshore_model._add_forcing_wind(wind_forcing)

                # Add pressure forcing for the offshore model (this doesnt happen normally in _add_forcing_wind() for overland models)
                if wind_forcing._source == ForcingSource.TRACK:
                    _offshore_model._add_pressure_forcing_from_grid(ds=ds["press"])

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _run_sfincs_offshore(self, sim_path):
        self._logger.info("Running offshore model...")
        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            success = _offshore_model.execute(strict=False)

            if not success:
                raise RuntimeError(
                    f"Running offshore SFINCS model failed. See {sim_path} for more information."
                )

    def _get_simulation_path(self) -> Path:
        if self.attrs.mode == Mode.risk:
            pass
        elif self.attrs.mode == Mode.single_event:
            path = (
                db.Database()
                .scenarios.get_database_path(get_input_path=False)
                .joinpath(
                    self._scenario.attrs.name,
                    "Flooding",
                    "simulations",
                    self._site.attrs.sfincs.offshore_model,
                )
            )
            return path
        else:
            raise ValueError(f"Unknown mode: {self.attrs.mode}")

    def _download_meteo(self, meteo_dir: Path):
        params = ["wind", "barometric_pressure", "precipitation"]
        lon = self._site.attrs.lon
        lat = self._site.attrs.lat

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
            path=meteo_dir,
            x_range=[lon - 10, lon + 10],
            y_range=[lat - 10, lat + 10],
            crs=CRS.from_epsg(4326),
        )

        # Download and collect data
        t0 = self.attrs.time.start_time
        if not isinstance(t0, datetime):
            t0 = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")

        t1 = self.attrs.time.end_time
        if not isinstance(t1, datetime):
            t1 = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")

        time_range = [t0, t1]

        gfs_conus.download(time_range)

    def _read_meteo(self, meteo_dir: Path) -> xr.Dataset:
        # Create an empty list to hold the datasets
        datasets = []

        # Loop over each file and create a new dataset with a time coordinate
        for filename in sorted(glob.glob(str(meteo_dir.joinpath("*.nc")))):
            # Open the file as an xarray dataset
            ds = xr.open_dataset(filename)

            # Extract the timestring from the filename and convert to pandas datetime format
            time_str = filename.split(".")[-2]
            time = pd.to_datetime(time_str, format="%Y%m%d_%H%M")

            # Add the time coordinate to the dataset
            ds["time"] = time

            # Append the dataset to the list
            datasets.append(ds)

        # Concatenate the datasets along the new time coordinate
        ds = xr.concat(datasets, dim="time")
        ds.raster.set_crs(4326)
        ds = ds.rename({"barometric_pressure": "press"})
        ds = ds.rename({"precipitation": "precip"})

        return ds

    def _get_observed_wl_data(
        self,
        units: UnitTypesLength = UnitTypesLength("meters"),
        source: str = "noaa_coops",
        out_path: str | os.PathLike = None,
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        path: str | os.PathLike
            Path to store the observed/imported waterlevel data.
        station_id : int
            NOAA observation station ID.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
        """
        wl_df = pd.DataFrame()

        for obs_point in self._site.attrs.obs_point:
            if obs_point.file:
                station_data = self._read_imported_waterlevels(obs_point.file)
            else:
                station_data = self._download_obs_point_data(
                    obs_point=obs_point, source=source
                )
            station_data = station_data.rename(columns={"waterlevel": obs_point.ID})
            station_data = station_data * UnitfulLength(
                value=1.0, units=UnitTypesLength("meters")
            ).convert(units)

            if wl_df.empty:
                wl_df = station_data
            else:
                wl_df = wl_df.join(station_data, how="outer")

        if out_path is not None:
            wl_df.to_csv(Path(out_path))

        return wl_df

    def _download_obs_point_data(
        self, obs_point: Obs_pointModel, source: str = "noaa_coops"
    ):
        # Get NOAA data
        source_obj = cht_station.source(source)
        df = source_obj.get_data(
            obs_point.ID, self.attrs.time.start_time, self.attrs.time.end_time
        )
        df = pd.DataFrame(df)  # Convert series to dataframe
        df = df.rename(columns={"v": 1})

        return df

    def _read_imported_waterlevels(self, path: str | os.PathLike):
        """Read waterlevels from an imported csv file.

        Parameters
        ----------
        path : str | os.PathLike
            Path to the csv file.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
        """
        df_temp = pd.read_csv(path, index_col=0, parse_dates=True)
        df_temp.index.names = ["time"]
        startindex = df_temp.index.get_loc(self.attrs.time.start_time, method="nearest")
        stopindex = df_temp.index.get_loc(self.attrs.time.end_time, method="nearest")
        df = df_temp.iloc[startindex:stopindex, :]
        return df
