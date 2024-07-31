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
from noaa_coops.station import COOPSAPIError
from pyproj import CRS

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallFromMeteo
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromGauged,
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.event.forcing.wind import WindFromMeteo
from flood_adapt.object_model.hazard.interface.events import (
    IEvent,
    IEventModel,
    Mode,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import Obs_pointModel
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
        self._logger = FloodAdaptLogging().getLogger(__name__)

    @property
    def site(self):
        return self.database.site

    def process(self, scenario: IScenario):
        """Preprocess, run and postprocess offshore model to obtain water levels for boundary condition of the overland model."""
        self._scenario = scenario
        self.meteo_ds = None
        sim_path = self._get_simulation_path()

        require_offshore_run = any(
            forcing._source == ForcingSource.MODEL
            for forcing in self.attrs.forcings.values()
            if forcing is not None
        )

        if require_offshore_run:
            self.download_meteo()
            self.meteo_ds = self.read_meteo()

            self._preprocess_sfincs_offshore(sim_path)
            self._run_sfincs_offshore(sim_path)

        if self.attrs.mode == Mode.risk:
            self._process_risk_event()
        else:
            self._process_single_event(sim_path)

    def _process_risk_event(self):
        # TODO implement / make a separate class for risk events
        pass

    def _process_single_event(self, sim_path: str | os.PathLike):
        if self.site.attrs.sfincs.offshore_model is None:
            raise ValueError(
                f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.__class__.__name__}'"
            )

        self._logger.info("Collecting forcing data ...")
        for forcing in self.attrs.forcings.values():
            if forcing is None:
                continue

            # FIXME added temp implementations here to make forcing.get_data() succeed,
            # move this to the forcings themselves?
            if isinstance(
                forcing, (WaterlevelFromModel, RainfallFromMeteo, WindFromMeteo)
            ):
                forcing.path = sim_path
            elif isinstance(forcing, WaterlevelFromGauged):
                out_path = sim_path / "waterlevels.csv"
                self._get_observed_wl_data(out_path=out_path)
                forcing.path = out_path

    def _preprocess_sfincs_offshore(self, sim_path: str | os.PathLike):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        This function is reused for ForcingSources: MODEL, TRACK, and GAUGED.

        Args:
            sim_path path to the root of the offshore model
        """
        self._logger.info("Preparing offshore model to generate waterlevels...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

        # Initialize
        if os.path.exists(sim_path):
            shutil.rmtree(sim_path)
        os.makedirs(sim_path, exist_ok=True)

        template_offshore = self.database.static_path.joinpath(
            "templates", self.site.attrs.sfincs.offshore_model
        )
        with SfincsAdapter(model_root=template_offshore) as _offshore_model:
            # Edit offshore model
            _offshore_model.set_timing(self.attrs)

            # Add water levels
            physical_projection = self.database.projections.get(
                self._scenario.attrs.projection
            ).get_physical_projection()
            _offshore_model._add_bzs_from_bca(self.attrs, physical_projection)

            # Add wind and if applicable pressure forcing from meteo data
            wind_forcing = self.attrs.forcings[ForcingType.WIND]
            if wind_forcing is not None:
                # Add wind forcing
                _offshore_model._add_forcing_wind(
                    wind_forcing
                )  # forcing.process() will download meteo if required. forcing.process is called by event.process()

                # Add pressure forcing for the offshore model (this doesnt happen normally in _add_forcing_wind() for overland models)
                if wind_forcing._source == ForcingSource.TRACK:
                    _offshore_model._add_pressure_forcing_from_grid(
                        ds=self.read_meteo()["press"]
                    )

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _run_sfincs_offshore(self, sim_path):
        self._logger.info("Running offshore model...")
        from flood_adapt.integrator.sfincs_adapter import SfincsAdapter

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
            path = self.database.scenarios.get_database_path(
                get_input_path=False
            ).joinpath(
                self._scenario.attrs.name,
                "Flooding",
                "simulations",
                self.site.attrs.sfincs.offshore_model,
            )
            return path
        else:
            raise ValueError(f"Unknown mode: {self.attrs.mode}")

    def download_meteo(
        self,
        *,
        t0: datetime | str = None,
        t1: datetime | str = None,
        meteo_dir: Path = None,
        lat: float = None,
        lon: float = None,
    ):
        params = ["wind", "barometric_pressure", "precipitation"]
        DEFAULT_METEO_PATH = self.database.output_path.joinpath("meteo")
        meteo_dir = meteo_dir or DEFAULT_METEO_PATH
        t0 = t0 or self.attrs.time.start_time
        t1 = t1 or self.attrs.time.end_time
        lat = lat or self.database.site.attrs.lat
        lon = lon or self.database.site.attrs.lon

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
        if not isinstance(t0, datetime):
            t0 = datetime.strptime(t0, "%Y%m%d %H%M%S")

        if not isinstance(t1, datetime):
            t1 = datetime.strptime(t1, "%Y%m%d %H%M%S")

        time_range = [t0, t1]

        gfs_conus.download(time_range)

    def read_meteo(
        self,
        *,
        t0: datetime | str = None,
        t1: datetime | str = None,
        meteo_dir: Path = None,
    ) -> xr.Dataset:
        # Create an empty list to hold the datasets
        datasets = []
        meteo_dir = meteo_dir or self.database.output_path.joinpath("meteo")
        t0 = t0 or self.attrs.time.start_time
        t1 = t1 or self.attrs.time.end_time

        if not isinstance(t0, datetime):
            t0 = datetime.strptime(t0, "%Y%m%d %H%M%S")
        if not isinstance(t1, datetime):
            t1 = datetime.strptime(t1, "%Y%m%d %H%M%S")

        if not meteo_dir.exists():
            meteo_dir.mkdir(parents=True)

        self.download_meteo(t0=t0, t1=t1, meteo_dir=meteo_dir)

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
        station_id: int = None,
        out_path: str | os.PathLike = None,
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        station_id : int | None
            NOAA observation station ID. If None, all observation stations in the site are downloaded.
        out_path: str | os.PathLike
            Path to store the observed/imported waterlevel data.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
        """
        wl_df = pd.DataFrame()
        if station_id is None:
            station_ids = [obs_point.ID for obs_point in self.site.attrs.obs_point]
        elif isinstance(station_id, int):
            station_ids = [station_id]

        obs_points = [p for p in self.site.attrs.obs_point if p.ID in station_ids]
        if not obs_points:
            self._logger.warning(
                f"Could not find observation stations with ID {station_id}."
            )
            return None

        for obs_point in obs_points:
            if obs_point.file:
                station_data = self._read_imported_waterlevels(obs_point.file)
            else:
                station_data = self._download_obs_point_data(
                    obs_point=obs_point, source=source
                )
                # Skip if data could not be downloaded
                if station_data is None:
                    continue
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
    ) -> pd.DataFrame | None:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        obs_point : Obs_pointModel
            Observation point model.
        source : str
            Source of the data.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel of the observation station as the column.
        None
            If the data could not be downloaded.
        """
        try:
            source_obj = cht_station.source(source)
            df = source_obj.get_data(
                obs_point.ID, self.attrs.time.start_time, self.attrs.time.end_time
            )
            df = pd.DataFrame(df)  # Convert series to dataframe
            df = df.rename(columns={"v": 1})

        except COOPSAPIError as e:
            self._logger.warning(
                f"Could not download tide gauge data for station {obs_point.ID}. {e}"
            )
            return None
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
