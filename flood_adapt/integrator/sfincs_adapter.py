from typing import Optional

from hydromt_sfincs import SfincsModel

# from flood_adapt.object_model.validate.config import validate_existence_root_folder


class SfincsAdapter:
    def load_overland_sfincs_model(self, model_root: Optional[str] = None):
        """Loads overland sfincs model based on a root directory.

        Args:
            model_root (str, optional): Root directory of overland sfincs model. Defaults to None.
        """
        # Check if model root exists
        # if validate_existence_root_folder(model_root):
        #    self.model_root = model_root

        self.sf_model = SfincsModel(root=model_root, mode="r+")
        self.sf_model.read()

    def add_wl_bc(self):
        """Changes waterlevel of overland sfincs model based on new waterlevel time series."""

        # Determine bnd points from reference overland model
        gdf_locs = self.sf_model.forcing["bzs"].vector.to_gdf()
        gdf_locs.crs = self.sf_model.crs

        # Go from 1 timeseries to timeseries for all boundary points
        df_ts = self.tide_ts
        wl = df_ts[0]
        for i in range(len(gdf_locs) - 1):
            col_name = i + 1
            df_ts[col_name] = wl

        # HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(
            name="bzs", df_ts=df_ts, gdf_locs=gdf_locs, merge=False
        )

    # def run_sfincs_models(self):
    #      pass

    # def add_time(self, input_times: dict):
    #      self.sf_model.config['tref'] = input_times['tref']
    #      self.sf_model.config['tstart'] = input_times['tstart']
    #      self.sf_model.config['tstop'] = input_times['tstop']

    # def add_floodwall(self, polygon_file: str = None):

    #     #HydroMT function: creates structure from dataframe
    #     #Needs to be completed in hydromt_sfincs
    #     self.sf_model.create_structures(structures_fn=polygon_file, stype='weir', overwrite=False)

    # def add_meteo_bc(self,
    #                  precip_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
    #                  ):
    #     #HydroMT function: set precipitation from times series
    #     self.sf_model.set_forcing(name='precip',ts=precip_ts,xy=xy_precip)

    # def add_discharge_bc(self,
    #                      dis_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
    #                      ):
    #     #HydroMT function: set river forcing from times series
    #     self.sf_model.set_forcing_1d(name='dis',ts=dis_ts,xy=self.sf_model.forcing['dis'].vector.to_gdf())
