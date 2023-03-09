from hydromt_sfincs import SfincsModel
from pathlib import Path
from typing import Dict, Tuple, List, Union
import pandas as pd
import xarray as xr
import geopandas as gpd
from flood_adapt.object_model.validate.config import validate_existence_root_folder

class SfincsAdapter():
    def __init__(self):
        ...

    def run_sfincs_models(self, )

    def load_sfincs_model(self, model_root: str = None):
            #Check if model root exists
            if validate_existence_root_folder(model_root):
                self.model_root = model_root
    
            self.sf_model = SfincsModel(root=model_root, mode='r+')
            self.sf_model.read()

    def add_time(self, input_times: dict):
         self.sf_model.config['tref'] = input_times['tref']
         self.sf_model.config['tstart'] = input_times['tstart']
         self.sf_model.config['tstop'] = input_times['tstop']

    def add_floodwall(self, polygon_file: str = None):
        
        #HydroMT function: creates structure from dataframe
        #Needs to be completed in hydromt_sfincs
        self.sf_model.create_structures(structures_fn=polygon_file, stype='weir', overwrite=False) 

    def add_wl_bc(self,
                  wl_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
                  ):
        
        #Go from 1 timeseries to timeseries for all boundary points

        
        #HydroMT function: set waterlevel forcing from time series
        self.sf_model.set_forcing_1d(name='waterlevel',ts=wl_ts ,xy=self.sf_model.forcing['bzs'].vector.to_gdf())
    
    def add_meteo_bc(self,
                     precip_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
                     ):
        #HydroMT function: set precipitation from times series
        self.sf_model.set_forcing_1d(name='precip',ts=precip_ts,xy=None) 

    def add_discharge_bc(self, 
                         dis_ts: Union[xr.DataArray, pd.DataFrame, Dict[str, pd.DataFrame]] = None
                         ):
        #HydroMT function: set river forcing from times series
        self.sf_model.set_forcing_1d(name='discharge',ts=dis_ts,xy=self.sf_model.forcing['dis'].vector.to_gdf())