import gc
import logging
import os
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd
import hydromt_sfincs.utils as utils
import numpy as np
import pandas as pd
import xarray as xr
from cht_tide.read_bca import SfincsBoundary
from cht_tide.tide_predict import predict
from hydromt_sfincs import SfincsModel

from flood_adapt.object_model.hazard.event.event import EventModel
from flood_adapt.object_model.hazard.event.historical_hurricane import (
    HistoricalHurricane,
)
from flood_adapt.object_model.hazard.measure.floodwall import FloodWallModel
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfrastructureModel,
)
from flood_adapt.object_model.hazard.measure.pump import PumpModel
from flood_adapt.object_model.interface.projections import PhysicalProjectionModel
from flood_adapt.object_model.io.unitfulvalue import (
    UnitfulLength,
    UnitTypesDischarge,
    UnitTypesLength,
    UnitTypesVolume,
)
from flood_adapt.object_model.site import Site

# from flood_adapt.object_model.validate.config import validate_existence_root_folder

logger = logging.getLogger(__name__)


class SfincsAdapter:
    def __init__(self, site: Site, model_root: Optional[str] = None):
        """Loads overland sfincs model based on a root directory.

        Args:
            model_root (str, optional): Root directory of overland sfincs model. Defaults to None.
        """
        self.sfincs_logger = logging.getLogger(__name__)
        self.sfincs_logger.handlers = []  # To ensure logging file path has reset
        self.sf_model = SfincsModel(
            root=model_root, mode="r+", logger=self.sfincs_logger
        )
        self.sf_model.read()
        self.site = site

    def __del__(self):
        # Close the log file associated with the logger
        for handler in self.sfincs_logger.handlers:
            handler.close()
        gc.collect()

    def set_timing(self, event: EventModel):
        """Changes model reference times based on event time series."""

        # Get start and end time of event
        tstart = event.time.start_time
        tstop = event.time.end_time

        # Update timing of the model
        self.sf_model.set_config("tref", tstart)
        self.sf_model.set_config("tstart", tstart)
        self.sf_model.set_config("tstop", tstop)

    def add_wind_forcing(
        self,
        timeseries: Union[str, os.PathLike] = None,
        const_mag: float = None,
        const_dir: float = None,
    ):
        """Add spatially constant wind forcing to sfincs model. Use timeseries or a constant magnitude and direction.

        Parameters
        ----------
        timeseries : Union[str, os.PathLike], optional
            path to file of timeseries file (.csv) which has three columns: time, magnitude and direction, by default None
        const_mag : float, optional
            magnitude of time-invariant wind forcing [m/s], by default None
        const_dir : float, optional
            direction of time-invariant wind forcing [deg], by default None
        """
        self.sf_model.setup_wind_forcing(
            timeseries=timeseries,
            magnitude=const_mag,
            direction=const_dir,
        )

    def add_wind_forcing_from_grid(self, ds: xr.DataArray):
        """Add spatially varying wind forcing to sfincs model.

        Parameters
        ----------
        ds : xr.DataArray
            Dataarray which should contain:
            - wind_u: eastward wind velocity [m/s]
            - wind_v: northward wind velocity [m/s]
            - spatial_ref: CRS
        """
        self.sf_model.setup_wind_forcing_from_grid(wind=ds)

    def add_pressure_forcing_from_grid(self, ds: xr.DataArray):
        """Add spatially varying barometric pressure to sfincs model.

        Parameters
        ----------
        ds : xr.DataArray
            Dataarray which should contain:
            - press: barometric pressure [Pa]
            - spatial_ref: CRS
        """
        self.sf_model.setup_pressure_forcing_from_grid(press=ds)

    def add_precip_forcing_from_grid(self, ds: xr.DataArray):
        """Add spatially varying precipitation to sfincs model.

        Parameters
        ----------
        precip : xr.DataArray
            Dataarray which should contain:
            - precip: precipitation rates [mm/hr]
            - spatial_ref: CRS
        """
        self.sf_model.setup_precip_forcing_from_grid(precip=ds, aggregate=False)

    def add_precip_forcing(
        self, timeseries: Union[str, os.PathLike] = None, const_precip: float = None
    ):
        """Add spatially uniform precipitation to sfincs model.

        Parameters
        ----------
        precip : Union[str, os.PathLike], optional
            timeseries file of precipitation (.csv) which has two columns: time and precipitation, by default None
        const_precip : float, optional
            time-invariant precipitation magnitude [mm/hr], by default None
        """
        # Add precipitation to SFINCS model
        self.sf_model.setup_precip_forcing(
            timeseries=timeseries, magnitude=const_precip
        )

    def add_wl_bc(self, df_ts: pd.DataFrame):
        """Add waterlevel dataframe to sfincs model.

        Parameters
        ----------
        df_ts : pd.DataFrame
            Dataframe with waterlevel time series at every boundary point (index of the dataframe should be time and every column should be an integer starting with 1)
        """
        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        if len(df_ts.columns) == 1:
            # Go from 1 timeseries to timeseries for all boundary points
            for i in range(1, len(gdf_locs)):
                df_ts[i + 1] = df_ts[1]

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    def add_bzs_from_bca(
        self, event: EventModel, physical_projection: PhysicalProjectionModel
    ):
        """Convert tidal constituents from bca file to waterlevel timeseries that can be read in by hydromt_sfincs"""

        sb = SfincsBoundary()
        sb.read_flow_boundary_points(Path(self.sf_model.root).joinpath("sfincs.bnd"))
        sb.read_astro_boundary_conditions(
            Path(self.sf_model.root).joinpath("sfincs.bca")
        )

        times = pd.date_range(
            start=event.time.start_time,
            end=event.time.end_time,
            freq="10T",
        )

        # Predict tidal signal and add SLR
        for bnd_ii in range(len(sb.flow_boundary_points)):
            tide_ii = (
                predict(sb.flow_boundary_points[bnd_ii].astro, times)
                + event.water_level_offset.convert(UnitTypesLength("meters"))
                + physical_projection.sea_level_rise.convert(UnitTypesLength("meters"))
            )

            if bnd_ii == 0:
                wl_df = pd.DataFrame(data={1: tide_ii}, index=times)
            else:
                wl_df[bnd_ii + 1] = tide_ii

        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="bzs", df_ts=wl_df, gdf_locs=gdf_locs, merge=False
        )

    def get_wl_df_from_offshore_his_results(self) -> pd.DataFrame:
        """Function to create a pd.Dataframe with waterlevels from the offshore model at the bnd locations of the overland model.

        Returns
        -------
        wl_df: pd.DataFrame
            time series of water level.
        """
        ds_his = utils.read_sfincs_his_results(
            Path(self.sf_model.root).joinpath("sfincs_his.nc"),
            crs=self.sf_model.crs.to_epsg(),
        )
        wl_df = pd.DataFrame(
            data=ds_his.point_zs.to_numpy(),
            index=ds_his.time.to_numpy(),
            columns=np.arange(1, ds_his.point_zs.to_numpy().shape[1] + 1, 1),
        )
        return wl_df

    def add_dis_bc(self, list_df: pd.DataFrame, site_river: list):
        """Changes discharge of overland sfincs model based on new discharge time series.

        Parameters
        ----------
        df_ts : pd.DataFrame
            time series of discharge, index should be Pandas DateRange
        """

        # Determine bnd points from reference overland model
        # ASSUMPTION: Order of the rivers is the same as the site.toml file
        if np.any(list_df):
            gdf_locs = self.sf_model.forcing["dis"].vector.to_gdf()
            gdf_locs.crs = self.sf_model.crs

            if len(list_df.columns) != len(gdf_locs):
                logging.error(
                    """The number of rivers of the site.toml does not match the
                              number of rivers in the SFINCS model. Please check the number
                              of coordinates in the SFINCS *.src file."""
                )
                raise ValueError(
                    "Number of rivers in site.toml and SFINCS template model not compatible"
                )

            # Test order of rivers is the same in the site file as in the SFICNS model
            for ii, river in enumerate((site_river)):
                if not (
                    np.abs(gdf_locs.geometry[ii + 1].x - river.x_coordinate) < 5
                    and np.abs(gdf_locs.geometry[ii + 1].y - river.y_coordinate) < 5
                ):
                    logging.error(
                        """The location and/or order of rivers in the site.toml does not match the
                                locations and/or order of rivers in the SFINCS model. Please check the
                                coordinates and their order in the SFINCS *.src file and ensure they are
                                consistent with the coordinates and order orf rivers in the site.toml file."""
                    )
                    raise ValueError(
                        "River coordinates in site.toml and SFINCS template model not compatible"
                    )
                    break

            self.sf_model.setup_discharge_forcing(
                timeseries=list_df, locations=gdf_locs, merge=False
            )

    def add_floodwall(self, floodwall: FloodWallModel, measure_path=Path):
        """Adds floodwall to sfincs model.

        Parameters
        ----------
        floodwall : FloodWallModel
            floodwall information
        """

        # HydroMT function: get geodataframe from filename
        polygon_file = measure_path.joinpath(floodwall.polygon_file)
        gdf_floodwall = self.sf_model.data_catalog.get_geodataframe(
            polygon_file, geom=self.sf_model.region, crs=self.sf_model.crs
        )

        # Add floodwall attributes to geodataframe
        gdf_floodwall["name"] = floodwall.name
        gdf_floodwall["z"] = floodwall.elevation.convert(UnitTypesLength("meters"))
        gdf_floodwall["par1"] = 0.6

        # HydroMT function: create floodwall
        self.sf_model.setup_structures(
            structures=gdf_floodwall, stype="weir", merge=True
        )

    def add_green_infrastructure(
        self, green_infrastructure: GreenInfrastructureModel, measure_path: Path
    ):
        """Adds green infrastructure to sfincs model.

        Parameters
        ----------
        green_infrastructure : GreenInfrastructureModel
            Green infrastructure information
        measure_path: Path
            Path of the measure folder
        """

        # HydroMT function: get geodataframe from filename
        if (
            green_infrastructure.selection_type == "polygon"
            or green_infrastructure.selection_type == "import_area"
        ):
            polygon_file = measure_path.joinpath(green_infrastructure.polygon_file)
        elif green_infrastructure.selection_type == "aggregation_area":
            # TODO this logic already exists in the database controller but cannot be used due to cyclic imports
            # Loop through available aggregation area types
            for aggr_dict in self.site.attrs.fiat.aggregation:
                # check which one is used in measure
                if not aggr_dict.name == green_infrastructure.aggregation_area_type:
                    continue
                # load geodataframe
                aggr_areas = gpd.read_file(
                    measure_path.parents[2] / "static" / "site" / aggr_dict.file,
                    engine="pyogrio",
                ).to_crs(4326)
                # keep only aggregation area chosen
                polygon_file = aggr_areas.loc[
                    aggr_areas[aggr_dict.field_name]
                    == green_infrastructure.aggregation_area_name,
                    ["geometry"],
                ].reset_index(drop=True)
        else:
            raise ValueError(
                f"The selection type: {green_infrastructure.selection_type} is not valid"
            )

        gdf_green_infra = self.sf_model.data_catalog.get_geodataframe(
            polygon_file,
            geom=self.sf_model.region,
            crs=self.sf_model.crs,
        )

        # Make sure no multipolygons are there
        gdf_green_infra = gdf_green_infra.explode()

        # Determine volume capacity of green infrastructure
        if green_infrastructure.height.value != 0.0:
            height = (
                green_infrastructure.height.convert(UnitTypesLength("meters"))
                * green_infrastructure.percent_area
            )
            volume = None
        elif green_infrastructure.volume.value != 0.0:
            height = None
            volume = green_infrastructure.volume.convert(UnitTypesVolume("m3"))

        # HydroMT function: create storage volume
        self.sf_model.setup_storage_volume(
            storage_locs=gdf_green_infra, volume=volume, height=height, merge=True
        )

    def add_pump(self, pump: PumpModel, measure_path: Path):
        """Adds pump to sfincs model.

        Parameters
        ----------
        pump : PumpModel
            pump information
        """

        # HydroMT function: get geodataframe from filename
        polygon_file = measure_path.joinpath(pump.polygon_file)
        gdf_pump = self.sf_model.data_catalog.get_geodataframe(
            polygon_file, geom=self.sf_model.region, crs=self.sf_model.crs
        )

        # HydroMT function: create floodwall
        self.sf_model.setup_drainage_structures(
            structures=gdf_pump,
            stype="pump",
            discharge=pump.discharge.convert(UnitTypesDischarge("m3/s")),
            merge=True,
        )

    def write_sfincs_model(self, path_out: Path):
        """Write all the files for the sfincs model

        Args:
            path_out (Path): new root of sfincs model
        """

        # Change model root to new folder
        self.sf_model.set_root(path_out, mode="w+")

        # Write sfincs files in output folder
        self.sf_model.write()

    def add_spw_forcing(
        self,
        historical_hurricane: HistoricalHurricane,
        database_path: Path,
        model_dir: Path,
    ):
        """Add spiderweb forcing to the sfincs model

        Parameters
        ----------
        historical_hurricane : HistoricalHurricane
            Information of the historical hurricane event
        database_path : Path
            Path of the main database
        model_dir : Path
            Output path of the model
        """

        historical_hurricane.make_spw_file(
            database_path=database_path, model_dir=model_dir, site=self.site
        )

    def set_config_spw(self, spw_name: str):
        self.sf_model.set_config("spwfile", spw_name)

    def turn_off_bnd_press_correction(self):
        self.sf_model.set_config("pavbnd", -9999)

    def add_obs_points(self):
        """add observation points provided in the site toml to SFINCS model"""

        if self.site.attrs.obs_point is not None:
            obs_points = self.site.attrs.obs_point
            names = []
            lat = []
            lon = []
            for pt in obs_points:
                names.append(pt.name)
                lat.append(pt.lat)
                lon.append(pt.lon)

            # create GeoDataFrame from obs_points in site file
            df = pd.DataFrame({"name": names})
            gdf = gpd.GeoDataFrame(
                df, geometry=gpd.points_from_xy(lon, lat), crs="EPSG:4326"
            )

            # Add locations to SFINCS file
            self.sf_model.setup_observation_points(locations=gdf, merge=False)

    def read_zsmax(self):
        """Read zsmax file and return absolute maximum water level over entire simulation"""
        self.sf_model.read_results()
        zsmax = self.sf_model.results["zsmax"].max(dim="timemax")
        return zsmax

    def read_zs_points(self):
        """Read water level (zs) timeseries at observation points
        Names are allocated from the site.toml.
        See also add_obs_points() above
        """

        self.sf_model.read_results()
        da = self.sf_model.results["point_zs"]
        df = pd.DataFrame(index=pd.DatetimeIndex(da.time), data=da.values)

        # get station names from site.toml
        if self.site.attrs.obs_point is not None:
            names = []
            descriptions = []
            obs_points = self.site.attrs.obs_point
            for pt in obs_points:
                names.append(pt.name)
                descriptions.append(pt.description)

        pt_df = pd.DataFrame({"Name": names, "Description": descriptions})
        gdf = gpd.GeoDataFrame(
            pt_df,
            geometry=gpd.points_from_xy(da.point_x.values, da.point_y.values),
            crs=self.sf_model.crs,
        )
        return df, gdf

    def get_mask(self):
        """Get mask with inactive cells from model"""
        mask = self.sf_model.grid["msk"]
        return mask

    def get_bedlevel(self):
        """Get bed level from model"""
        self.sf_model.read_results()
        zb = self.sf_model.results["zb"]
        return zb

    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """Get bounding box from model"""
        return self.sf_model.region

    def write_geotiff(self, zsmax, demfile: Path, floodmap_fn: Path):
        # read DEM and convert units to metric units used by SFINCS

        demfile_units = self.site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self.sf_model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self.site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
            floodmap_fn=str(floodmap_fn),
        )

    def downscale_hmax(self, zsmax, demfile: Path):
        # read DEM and convert units to metric units used by SFINCS
        demfile_units = self.site.attrs.dem.units
        dem_conversion = UnitfulLength(value=1.0, units=demfile_units).convert(
            UnitTypesLength("meters")
        )
        dem = dem_conversion * self.sf_model.data_catalog.get_rasterdataset(demfile)

        # determine conversion factor for output floodmap
        floodmap_units = self.site.attrs.sfincs.floodmap_units
        floodmap_conversion = UnitfulLength(
            value=1.0, units=UnitTypesLength("meters")
        ).convert(floodmap_units)

        hmax = utils.downscale_floodmap(
            zsmax=floodmap_conversion * zsmax,
            dep=floodmap_conversion * dem,
            hmin=0.01,
        )
        return hmax
