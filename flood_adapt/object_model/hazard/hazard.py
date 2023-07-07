import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.hazard.event.event_factory import EventFactory
from flood_adapt.object_model.hazard.event.eventset import EventSet
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.hazard.utils import cd
from flood_adapt.object_model.interface.events import Mode
from flood_adapt.object_model.interface.scenarios import ScenarioModel
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy


class Hazard:
    """class holding all information related to the hazard of the scenario
    includes functions to generate generic timeseries for the hazard models
    and to run the hazard models
    """

    name: str
    database_input_path: Path
    mode: Mode
    event_set: list[Event]
    physical_projection: PhysicalProjection
    hazard_strategy: HazardStrategy
    has_run: bool = False

    def __init__(self, scenario: ScenarioModel, database_input_path: Path) -> None:
        self.name = scenario.name
        self.database_input_path = database_input_path
        self.set_event(
            scenario.event
        )  # also setting the mode (single_event or risk here)
        self.set_hazard_strategy(scenario.strategy)
        self.set_physical_projection(scenario.projection)
        self.site = Site.load_file(
            database_input_path.parent / "static" / "site" / "site.toml"
        )
        self.set_simulation_paths()
        self.has_run = self.sfincs_has_run_check()

    def set_simulation_paths(self) -> None:
        if self.mode == "single_event":
            self.simulation_paths = [
                self.database_input_path.parent.joinpath(
                    "output",
                    "simulations",
                    self.name,
                    self.site.attrs.sfincs.overland_model,
                )
            ]
            # Create a folder name for the offshore model (will not be used if offshore model is not created)
            self.simulation_paths_offshore = [
                self.database_input_path.parent.joinpath(
                    "output",
                    "simulations",
                    self.name,
                    self.site.attrs.sfincs.offshore_model,
                )
            ]
        elif self.mode == "risk":  # risk mode requires an additional folder layer
            self.simulation_paths = []
            self.simulation_paths_offshore = []
            for subevent in self.event_set:
                self.simulation_paths.append(
                    self.database_input_path.parent.joinpath(
                        "output",
                        "simulations",
                        self.name,
                        subevent.attrs.name,
                        self.site.attrs.sfincs.overland_model,
                    )
                )
                # Create a folder name for the offshore model (will not be used if offshore model is not created)
                self.simulation_paths_offshore.append(
                    self.database_input_path.parent.joinpath(
                        "output",
                        "simulations",
                        self.name,
                        subevent.attrs.name,
                        self.site.attrs.sfincs.offshore_model,
                    )
                )

    def sfincs_has_run_check(self) -> bool:
        test_combined = False
        if len(self.simulation_paths) == 0:
            raise ValueError("The Scenario has not been initialized correctly.")
        else:
            for sfincs_path in self.simulation_paths:
                test1 = Path(sfincs_path).joinpath("sfincs_map.nc").exists()

                sfincs_log = Path(sfincs_path).joinpath("sfincs.log")

                if sfincs_log.exists():
                    with open(sfincs_log) as myfile:
                        if "Simulation finished" in myfile.read():
                            test2 = True
                        else:
                            test2 = False
                else:
                    test2 = False

                test_combined = (test1) & (test2)
                if test_combined is False:
                    break
        return test_combined

    def set_event(self, event: str) -> None:
        """Sets the actual Event template class list using the list of measure names
        Args:
            event_name (str): name of event used in scenario
        """
        event_set_path = (
            self.database_input_path / "events" / event / "{}.toml".format(event)
        )
        # set mode (probabilistic_set or single_event)
        self.mode = Event.get_mode(event_set_path)
        if self.mode == "single_event":
            event_paths = [event_set_path]
            self.probabilities = [1]
        elif self.mode == "risk":
            event_paths = []
            event_set = EventSet.load_file(event_set_path)
            self.frequencies = event_set.attrs.frequency
            subevents = event_set.attrs.subevent_name
            for subevent in subevents:
                event_path = (
                    self.database_input_path
                    / "events"
                    / event
                    / subevent
                    / "{}.toml".format(subevent)
                )
                event_paths.append(event_path)

        # parse event config file to get event template
        self.event_set = []
        for event_path in event_paths:
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            self.event_set.append(
                EventFactory.get_event(template).load_file(event_path)
            )
        if self.mode == "single_event":
            self.event = self.event_set[
                0
            ]  # TODO: makes this neater? Might change with the new workflow

    def set_physical_projection(self, projection: str) -> None:
        projection_path = (
            self.database_input_path / "Projections" / projection / f"{projection}.toml"
        )
        self.physical_projection = Projection.load_file(
            projection_path
        ).get_physical_projection()

    def set_hazard_strategy(self, strategy: str) -> None:
        strategy_path = (
            self.database_input_path / "Strategies" / strategy / f"{strategy}.toml"
        )
        self.hazard_strategy = Strategy.load_file(strategy_path).get_hazard_strategy()

    # no write function is needed since this is only used internally

    def add_wl_ts(self):
        """adds total water level timeseries to hazard object"""
        # generating total time series made of tide, slr and water level offset,
        # only for Synthetic and historical from nearshore
        if self.event.attrs.template == "Synthetic":
            self.event.add_tide_and_surge_ts()
            self.wl_ts = self.event.tide_surge_ts
        elif self.event.attrs.template == "Historical_nearshore":
            wl_df = self.event.tide_surge_ts
            self.wl_ts = wl_df
        # In both cases add the slr and offset
        self.wl_ts[1] = (
            self.wl_ts[1]
            + self.event.attrs.water_level_offset.convert("meters")
            + self.physical_projection.attrs.sea_level_rise.convert("meters")
        )
        return self

    def add_discharge(self):
        """adds discharge timeseries to hazard object"""
        # constant for all event templates, additional: shape for Synthetic or timeseries for all historic
        self.event.add_dis_ts()
        self.dis_ts = self.event.dis_ts
        return self

    @staticmethod
    def get_event_object(event_path):  # TODO This could be used above as well?
        mode = Event.get_mode(event_path)
        if mode == "single_event":
            # parse event config file to get event template
            template = Event.get_template(event_path)
            # use event template to get the associated event child class
            return EventFactory.get_event(template).load_file(event_path)
        elif mode == "risk":
            return EventSet.load_file(event_path)

    def preprocess_models(self):
        # Preprocess all hazard model input
        self.preprocess_sfincs()
        # add other models here

    def run_models(self):
        self.run_sfincs()

    def postprocess_models(self):
        # Postprocess all hazard model input
        self.postprocess_sfincs()
        # add other models here

    def run_sfincs(self):
        # Run new model(s)

        sfincs_exec = (
            self.database_input_path.parents[2] / "system" / "sfincs" / "sfincs.exe"
        )

        for simulation_path in self.simulation_paths:
            with cd(simulation_path):
                sfincs_log = "sfincs.log"
                with open(sfincs_log, "w") as log_handler:
                    subprocess.run(sfincs_exec, stdout=log_handler)

        # Indicator that hazard has run
        self.__setattr__("has_run", True)

    def run_sfincs_offshore(self):
        # Run offshore model(s)

        sfincs_exec = (
            self.database_input_path.parents[2] / "system" / "sfincs" / "sfincs.exe"
        )

        for simulation_path in self.simulation_paths_offshore:
            with cd(simulation_path):
                sfincs_log = "sfincs.log"
                with open(sfincs_log, "w") as log_handler:
                    subprocess.run(sfincs_exec, stdout=log_handler)

        # Indicator that hazard has run
        self.__setattr__("has_run", True)

    def preprocess_sfincs(
        self,
    ):
        base_path = self.database_input_path.parent
        path_in = base_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.overland_model
        )
        event_dir = self.database_input_path / "events" / self.event.attrs.name

        for ii, event in enumerate(self.event_set):
            self.event = event  # set current event to ii-th event in event set
            # Load overland sfincs model
            model = SfincsAdapter(model_root=path_in)

            # adjust timing of model
            model.set_timing(self.event.attrs)

            # Download meteo files if necessary
            if (
                self.event.attrs.wind.source == "map"
                or self.event.attrs.rainfall.source == "map"
            ):
                ds = self.event.download_meteo(site=self.site, path=event_dir)
                ds = ds.rename({"barometric_pressure": "press"})
                ds = ds.rename({"precipitation": "precip"})
            else:
                ds = None

            # Generate and change water level boundary condition
            template = self.event.attrs.template
            if template == "Synthetic" or template == "Historical_nearshore":
                self.add_wl_ts()
            elif template == "Historical_offshore":
                self.run_offshore_model(ds=ds, ii=ii)
            elif template == "Hurricane":
                raise NotImplementedError
            model.add_wl_bc(self.wl_ts)

            # Generate and change discharge boundary condition
            self.add_discharge()
            model.add_dis_bc(self.dis_ts)

            # Generate and add rainfall boundary condition
            if self.event.attrs.rainfall.source == "map":
                model.add_precip_forcing_from_grid(ds=ds)
            elif self.event.attrs.rainfall.source == "timeseries":
                model.add_precip_forcing(timeseries=event_dir.joinpath("rainfall.csv"))
            elif self.event.attrs.wind.source == "constant":
                model.add_precip_forcing(
                    const_precip=self.event.attrs.rainfall.constant_intensity.convert(
                        "mm/hr"
                    )
                )

            # Generate and add wind boundary condition
            if self.event.attrs.wind.source == "map":
                model.add_wind_forcing_from_grid(ds=ds)
            elif self.event.attrs.wind.source == "timeseries":
                model.add_wind_forcing(timeseries=event_dir.joinpath("wind.csv"))
            elif self.event.attrs.wind.source == "constant":
                model.add_wind_forcing(
                    const_mag=self.event.attrs.wind.constant_speed.convert("m/s"),
                    const_dir=self.event.attrs.wind.constant_direction.value,
                )

            # Add measures if included
            if self.hazard_strategy.measures is not None:
                for measure in self.hazard_strategy.measures:
                    measure_path = base_path.joinpath(
                        "input", "measures", measure.attrs.name
                    )
                    if measure.attrs.type == "floodwall":
                        model.add_floodwall(
                            floodwall=measure.attrs, measure_path=measure_path
                        )

            # write sfincs model in output destination
            model.write_sfincs_model(path_out=self.simulation_paths[ii])

    def run_offshore_model(self, ds: xr.DataArray, ii: int):
        """Run offshore model to obtain water levels for boundary condition of the nearshore model

        Args:
            ds (xr.DataArray): DataArray with meteo information (downloaded using event.download_meteo())
            ii (int): Iterator for event set
        """
        # Determine folders for offshore model
        base_path = self.database_input_path.parent
        path_in_offshore = base_path.joinpath(
            "static", "templates", self.site.attrs.sfincs.offshore_model
        )
        event_dir = self.database_input_path / "events" / self.event.attrs.name

        # Initiate offshore model
        offshore_model = SfincsAdapter(model_root=path_in_offshore)

        # Set timing of offshore model (same as overland model)
        offshore_model.set_timing(self.event.attrs)

        # set wl of offshore model
        offshore_model.add_bzs_from_bca(
            self.event.attrs, self.physical_projection.attrs
        )

        # Add wind and if applicable pressure forcing from files.
        if self.event.attrs.wind.source == "map":
            offshore_model.add_wind_forcing_from_grid(ds=ds)
            offshore_model.add_pressure_forcing_from_grid(ds=ds)
        elif self.event.attrs.wind.source == "timeseries":
            offshore_model.add_wind_forcing(timeseries=event_dir.joinpath("wind.csv"))
        elif self.event.attrs.wind.source == "constant":
            offshore_model.add_wind_forcing(
                const_mag=self.event.attrs.wind.constant_speed.value,
                const_dir=self.event.attrs.wind.constant_direction.value,
            )

        # write sfincs model in output destination
        offshore_model.write_sfincs_model(path_out=self.simulation_paths_offshore[ii])

        # Run the actual SFINCS model
        self.run_sfincs_offshore()

        # take his results from offshore model as input for wl bnd
        self.wl_ts = offshore_model.get_wl_df_from_offshore_his_results()

    def postprocess_sfincs(self):
        if self.mode == "single_event":
            ...  # TODO: create geotiff?
        elif self.mode == "probabilistic_set":
            self.calculate_rp_floodmaps()
            self.calculate_floodfrequency_map()

    def __eq__(self, other):
        if not isinstance(other, Hazard):
            # don't attempt to compare against unrelated types
            return NotImplemented
        test1 = self.event_set == other.event_set  # TODO verify this works
        test2 = self.physical_projection == other.physical_projection
        test3 = self.hazard_strategy == other.hazard_strategy
        return test1 & test2 & test3

    def calculate_rp_floodmaps(self):
        floodmap_rp = self.site.attrs.risk.return_periods
        frequencies = self.frequencies

        zs_maps = []
        for ii, simulation_path in enumerate(self.simulation_paths):
            # read zsmax data from overland sfincs model
            sim = SfincsAdapter(model_root=simulation_path)
            zsmax = sim.read_zsmax().load()
            zs_maps.append(zsmax.stack(z=("x", "y")))

        # Create RP flood maps

        # 1a: make a table of all water levels and associated frequencies
        zs = xr.concat(zs_maps, pd.Index(frequencies, name="frequency"))
        freq = np.tile(frequencies, (zs.shape[1], 1)).transpose()

        # 1b: sort water levels in descending order and include the frequencies in the sorting process
        # (i.e. each h-value should be linked to the same p-values as in step 1a)
        sort_index = zs.argsort(axis=0)
        sorted_prob = np.flipud(np.take_along_axis(freq, sort_index, axis=0))
        sorted_zs = np.flipud(np.take_along_axis(zs.values, sort_index, axis=0))

        # 1c: Compute exceedance probabilities of water depths
        # Method: accumulate probabilities from top to bottom
        prob_exceed = np.cumsum(sorted_prob, axis=0)

        # 1d: Compute return periods of water depths
        # Method: simply take the inverse of the exceedance probability (1/Pex)
        rp_zs = 1.0 / prob_exceed

        # For each return period (T) of interest do the following:
        # For each grid cell do the following:
        # Use the table from step [1d] as a “lookup-table” to derive the T-year water depth. Use a 1-d interpolation technique:
        # h(T) = interp1 (log(T*), h*, log(T))
        # in which t* and h* are the values from the table and T is the return period (T) of interest
        # The resulting T-year water depths for all grids combined form the T-year hazard map
        rp_da = xr.DataArray(rp_zs, dims=zs.dims)

        no_data_value = -999  # in SFINCS
        sorted_zs = xr.where(sorted_zs == no_data_value, np.nan, sorted_zs)

        h = np.where(
            np.all(np.isnan(sorted_zs), axis=0), np.nan, 0
        )  # do not calculate for cells with no data value
        valid_cells = np.where(~np.isnan(h))[0]

        zs_rp_maps = []

        for rp in floodmap_rp:
            print(f"Evaluating {rp}-year return period...")
            if rp <= rp_da.max() and rp >= rp_da.min():
                # using lower threshold
                # TODO: improve speed
                for jj in valid_cells:
                    h[jj] = np.interp(
                        np.log10(rp),
                        np.log10(rp_da[::-1, jj]),
                        sorted_zs[::-1, jj],
                        left=0,
                    )

                    # ToDo: decide on interpolation: lower threshold, linear, upper threshold (most risk averse/conservative),
                    #  now interpolating

                    # h[valid_cells] = np.nanmax(np.where(rp - rp_da[:, valid_cells] > 0, sorted_zs[:, valid_cells], 0),
                    #                            axis=0)

                    # Code to reuse to speed things up
                    # rp_array = matlib.repmat(hist_inun.rp, hist_inun.shape[1], 1)
                    # rp_da = xr.DataArray(rp_array.transpose(), coords=hist_inun.coords, dims=hist_inun.dims)
                    #
                    # diff_da = np.subtract(rp_da, matlib.repmat(pl_tile.mrp[use_ind], hist_inun.rp.size, 1))
                    # diff_da = xr.where(diff_da < 0, np.nan, diff_da)
                    # index2 = diff_da.argmin(dim='rp', skipna='True')
                    #
                    # inun_low = hist_inun[index2 - 1, :]
                    # inun_up = hist_inun[index2, :]
                    # regress_slope = (inun_up - inun_low) / (inun_up.rp - inun_low.rp)
                    #
                    # pl_height[use_ind] = inun_low.drop('rp') + regress_slope * (pl_tile.mrp[use_ind] - inun_low.rp)

            elif rp > rp_da.max():
                print(
                    f"{rp}-year RP larger than maximum return period in the event ensemble, which is {int(rp_da.max())}. Using max. water levels across all events"
                )
                h[valid_cells] = sorted_zs[0, valid_cells]

            elif rp < rp_da.min():
                # ToDo: only valid if no area is below MSL
                h[valid_cells] = 0
                print(
                    f"{rp}-year RP smaller than minimum return period in the event ensemble, which is {int(rp_da.min())} years. Setting water levels to zero for RP {rp}-years"
                )

            zs_rp_da = xr.DataArray(data=h, coords={"z": zs["z"]})
            zs_rp_maps.append(zs_rp_da.unstack())


        # write netcdf with water level, add new dimension for rp
        zs_rp = xr.concat(zs_rp_maps, pd.Index(floodmap_rp, name="rp"))
        zs_rp = zs_rp.rio.write_crs("epsg:26917", inplace=True)
        zs_rp = zs_rp.to_dataset(name="risk_maps")

        fn_rp = self.simulation_paths[0].parent.parent.joinpath("rp_water_level.nc")
        zs_rp.to_netcdf(fn_rp)

    def calculate_floodfrequency_map(self):
        raise NotImplementedError
        # CFRSS code below

        # # Create Flood frequency map
        # zs_maps = []
        # dem = read_geotiff(config_dict, scenarioDict)
        # freq_dem = np.zeros_like(dem)
        # for ii, zs_max_path in enumerate(results_full_path):
        #     # read zsmax data
        #     fn_dat = zs_max_path.parent.joinpath('sfincs.ind')
        #     data_ind = np.fromfile(fn_dat, dtype="i4")
        #     index = data_ind[1:] - 1  # because python starts counting at 0
        #     fn_dat = zs_max_path
        #     data_zs_orig = np.fromfile(fn_dat, dtype="f4")
        #     data_zs = data_zs_orig[1:int(len(data_zs_orig) / 2) - 1]
        #     da = xr.DataArray(data=data_zs,
        #                     dims=["index"],
        #                     coords=dict(index=(["index"], index)))
        #     zs_maps.append(da) # save for RP map calculation

        #     # create flood depth hmax

        #     nmax = int(sf_input_df.loc['nmax'])
        #     mmax = int(sf_input_df.loc['mmax'])
        #     zsmax = np.zeros(nmax * mmax) - 999.0
        #     zsmax[index] = data_zs
        #     zsmax_dem = resample_sfincs_on_dem(zsmax, config_dict, scenarioDict)
        #     # calculate max. flood depth as difference between water level zs and dem, do not allow for negative values
        #     hmax_dem = zsmax_dem - dem
        #     hmax_dem = np.where(hmax_dem < 0, 0, hmax_dem)

        #     # For every grid cell, take the sum of frequencies for which it was flooded (above threshold). The sresult is frequency of flooding for that grid cell
        #     freq_dem += np.where(hmax_dem > threshold, probability[ii], 0)

        # no_datavalue = float(config_dict['no_data_value'])
        # freq_dem = np.where(np.isnan(hmax_dem), no_datavalue, freq_dem)

        # # write flooding frequency to geotiff
        # demfile = Path(scenarioDict['static_path'], 'dem', config_dict['demfilename'])
        # dem_ds = gdal.Open(str(demfile))
        # [cols, rows] = dem.shape
        # driver = gdal.GetDriverByName("GTiff")
        # fn_tif = str(result_folder.joinpath('Flood_frequency.tif'))
        # outdata = driver.Create(fn_tif, rows, cols, 1, gdal.GDT_Float32)
        # outdata.SetGeoTransform(dem_ds.GetGeoTransform())  ##sets same geotransform as input
        # outdata.SetProjection(dem_ds.GetProjection())  ##sets same projection as input
        # outdata.GetRasterBand(1).WriteArray(freq_dem)
        # outdata.GetRasterBand(1).SetNoDataValue(no_datavalue)  ##if you want these values transparent
        # outdata.SetMetadata({k: str(v) for k, v in scenarioDict.items()})
        # logging.info("Created geotiff file with flood frequency.")
        # print("Created geotiff file with flood frequency.", file=sys.stdout, flush=True)

        # outdata.FlushCache()  ##saves to disk!!
        # outdata = None
        # band = None
        # dem_ds = None
