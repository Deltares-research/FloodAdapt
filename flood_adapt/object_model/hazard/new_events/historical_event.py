import glob
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import cht_observations.observation_stations as cht_station
import pandas as pd
import xarray as xr
from cht_meteo.meteo import (
    MeteoGrid,
    MeteoSource,
)
from pyproj import CRS

import flood_adapt.config as FloodAdapt_config
from flood_adapt.dbs_controller import Database
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingType,
)
from flood_adapt.object_model.hazard.new_events.forcing.waterlevels import (
    WaterlevelFromModel,
)
from flood_adapt.object_model.hazard.new_events.forcing.wind import (
    WindFromTrack,
)
from flood_adapt.object_model.hazard.new_events.new_event import IEvent
from flood_adapt.object_model.hazard.new_events.new_event_models import (
    HistoricalEventModel,
)
from flood_adapt.object_model.interface.events import (
    Mode,
)
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.interface.site import ISite, Obs_pointModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength
from flood_adapt.object_model.utils import cd


class HistoricalEvent(IEvent):
    attrs: HistoricalEventModel

    def __init__(self):
        self._logger = FloodAdaptLogging().getLogger(__name__)
        self._site: ISite = Database().site

    def process(self, scenario: ScenarioModel):
        """Preprocess, run and postprocess offshore model to obtain water levels for boundary condition of the overland model."""
        self._scenario = scenario

        if self.attrs.mode == Mode.risk:
            self._process_risk_event(scenario)
        else:
            self._process_single_event(scenario)

    def _process_risk_event(self, scenario: ScenarioModel):
        # TODO implement / make a separate class for risk events
        pass

    def _process_single_event(self, scenario: ScenarioModel):
        if self._site.attrs.sfincs.offshore_model is None:
            raise ValueError(
                f"An offshore model needs to be defined in the site.toml with sfincs.offshore_model to run an event of type '{self.__class__.__name__}'"
            )
        sim_path = self._get_simulation_path()

        self._logger.info("Preparing offshore model to generate tide and surge...")
        self._preprocess_sfincs_offshore(sim_path)

        self._logger.info("Running offshore model...")
        self._run_sfincs_offshore(sim_path)  # TODO check if we can skip this?

        self._logger.info("Collecting forcing data ...")
        forcing_dir = sim_path.joinpath("generated_forcings")
        os.makedirs(forcing_dir, exist_ok=True)

        for forcing in self.attrs.forcings.values():
            if forcing is not None:
                self._logger.info(f"Writing {forcing._type} data ...")
                forcing_path = forcing_dir.joinpath(f"{forcing._type}.csv")

                if isinstance(
                    forcing, WaterlevelFromModel
                ):  # FIXME make this a method of the forcing?
                    self._get_waterlevel_at_boundary_from_offshore(sim_path).to_csv(
                        forcing_path
                    )
                elif isinstance(forcing, WindFromTrack):
                    self._download_observed_wl_data().to_csv(forcing_path)
                else:
                    forcing.to_csv(forcing_path)

        # turn off pressure correction at the boundaries because the effect of
        # atmospheric pressure is already included in the water levels from the
        # offshore model
        # TODO move line below to sfincsadapter overland code
        # model.turn_off_bnd_press_correction()

    def _preprocess_sfincs_offshore(self, sim_path):
        """Preprocess offshore model to obtain water levels for boundary condition of the nearshore model.

        Args:
            ds (xr.DataArray): DataArray with meteo information (downloaded using event._download_meteo())
        """
        # Download meteo data
        meteo_dir = Database().output_path.joinpath("meteo")
        if not meteo_dir.is_dir():
            os.mkdir(Database().output_path.joinpath("meteo"))

        ds = self._download_meteo(site=self._site, path=meteo_dir)
        ds = ds.rename({"barometric_pressure": "press"})
        ds = ds.rename({"precipitation": "precip"})

        # Initialize
        if os.path.exists(sim_path):
            shutil.rmtree(sim_path)
        os.makedirs(sim_path, exist_ok=True)

        template_offshore = Database().static_path.joinpath(
            "templates", self._site.attrs.sfincs.offshore_model
        )
        with SfincsAdapter(model_root=template_offshore) as _offshore_model:
            # Edit offshore model
            _offshore_model.set_timing(self.attrs)

            # Add water levels
            physical_projection = (
                Database()
                .projections.get(self._scenario.projection)
                .get_physical_projection()
            )
            _offshore_model._add_bzs_from_bca(self.attrs, physical_projection)

            # Add wind and if applicable pressure forcing from meteo data
            # TODO make it easier to access and change forcings
            wind_forcing = self.attrs.forcings[ForcingType.WIND]
            if wind_forcing is not None:
                _offshore_model._add_forcing_wind(wind_forcing)

                if isinstance(wind_forcing, WindFromTrack):
                    # _offshore_model._add_wind_forcing_from_grid(ds=ds)
                    # line above is done is done in _add_forcing_wind() the adapter
                    # TODO turn off pressure correction in overland model
                    _offshore_model._add_pressure_forcing_from_grid(ds=ds["press"])

            # write sfincs model in output destination
            _offshore_model.write(path_out=sim_path)

    def _run_sfincs_offshore(self, sim_path):
        if not FloodAdapt_config.get_system_folder():
            raise ValueError(
                """
                SYSTEM_FOLDER environment variable is not set. Set it by calling FloodAdapt_config.set_system_folder() and provide the path.
                The path should be a directory containing folders with the model executables
                """
            )

        sfincs_exec = FloodAdapt_config.get_system_folder() / "sfincs" / "sfincs.exe"

        with cd(sim_path):
            sfincs_log = Path(sim_path) / "sfincs.log"
            with open(sfincs_log, "w") as log_handler:
                process = subprocess.run(sfincs_exec, stdout=log_handler)
                if process.returncode != 0:
                    raise RuntimeError(
                        f"Running offshore SFINCS model failed. See {sfincs_log} for more information."
                    )

    def _get_waterlevel_at_boundary_from_offshore(self, sim_path) -> pd.DataFrame:
        with SfincsAdapter(model_root=sim_path) as _offshore_model:
            return _offshore_model._get_wl_df_from_offshore_his_results()

    def _get_simulation_path(self) -> Path:
        if self.attrs.mode == Mode.risk:
            pass
        elif self.attrs.mode == Mode.single_event:
            path = (
                Database()
                .scenarios.get_database_path(get_input_path=False)
                .joinpath(
                    self._scenario.name,
                    "Flooding",
                    "simulations",
                    self._site.attrs.sfincs.offshore_model,
                )
            )
            return path
        else:
            raise ValueError(f"Unknown mode: {self.attrs.mode}")

    def _download_meteo(self, path: Path):
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
            path=path,
            x_range=[lon - 10, lon + 10],
            y_range=[lat - 10, lat + 10],
            crs=CRS.from_epsg(4326),
        )

        # Download and collect data
        t0 = datetime.strptime(self.attrs.time.start_time, "%Y%m%d %H%M%S")
        t1 = datetime.strptime(self.attrs.time.end_time, "%Y%m%d %H%M%S")
        time_range = [t0, t1]

        gfs_conus.download(time_range)

        # Create an empty list to hold the datasets
        datasets = []

        # Loop over each file and create a new dataset with a time coordinate
        for filename in sorted(glob.glob(str(path.joinpath("*.nc")))):
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

        return ds

    def _download_observed_wl_data(
        self,
        units: UnitTypesLength = UnitTypesLength("meters"),
        source: str = "noaa_coops",
    ) -> pd.DataFrame:
        """Download waterlevel data from NOAA station using station_id, start and stop time.

        Parameters
        ----------
        station_id : int
            NOAA observation station ID.

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and the waterlevel for each observation station as columns.
        """
        wl_df = pd.DataFrame()

        for obs_point in self._site.attrs.obs_point:
            station_data = self._download_obs_point_data(
                obs_point=obs_point, source=source
            )
            station_data.rename(columns={"waterlevel": obs_point.ID})

            conversion_factor = UnitfulLength(
                value=1.0, units=UnitTypesLength("meters")
            ).convert(units)
            station_data = conversion_factor * station_data

            wl_df = pd.concat([wl_df, station_data], axis=1)

        return wl_df

    def _download_obs_point_data(
        self, obs_point: Obs_pointModel, source: str = "noaa_coops"
    ):
        if obs_point.file is not None:
            df_temp = HistoricalEvent.read_csv(obs_point.file)
            startindex = df_temp.index.get_loc(
                self.attrs.time.start_time, method="nearest"
            )
            stopindex = df_temp.index.get_loc(
                self.attrs.time.end_time, method="nearest"
            )
            df = df_temp.iloc[startindex:stopindex, :]
        else:
            # Get NOAA data
            source_obj = cht_station.source(source)
            df = source_obj.get_data(
                obs_point.ID, self.attrs.time.start_time, self.attrs.time.end_time
            )
            df = pd.DataFrame(df)  # Convert series to dataframe
            df = df.rename(columns={"v": 1})

        return df

    @staticmethod
    def read_csv(csvpath: str | Path) -> pd.DataFrame:
        """Read a timeseries file and return a pd.Dataframe.

        Parameters
        ----------
        csvpath : Union[str, os.PathLike]
            path to csv file

        Returns
        -------
        pd.DataFrame
            Dataframe with time as index and waterlevel as first column.
        """
        df = pd.read_csv(csvpath, index_col=0, header=None)
        df.index.names = ["time"]
        df.index = pd.to_datetime(df.index)
        return df
