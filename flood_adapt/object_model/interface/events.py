from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import hydromt.raster  # noqa: F401
import numpy as np
import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.io.unitfulvalue import UnitTypesLength
from flood_adapt.object_model.models.events import (
    Mode,
    SyntheticModel,
)

from .objectModel import IDbsObject, DbsObjectModel


class IEvent(ABC):

    @staticmethod
    @abstractmethod
    def get_template(filepath: Path):
        """create Synthetic from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def get_mode(filepath: Path) -> Mode:
        """get mode of the event (single or risk) from toml file"""
        ...

    @staticmethod
    @abstractmethod
    def timeseries_shape(
        shape_type: str, duration: float, peak: float, **kwargs
    ) -> np.ndarray:
        """create generic function to create shape timeseries for rainfall and discharge

        Parameters
        ----------
        shape_type : str
            type of the shape: accepted types are gaussian, block or triangle
        duration : float
            total duration (in seconds) of the event
        peak : float
            shape_peak value

        Optional Parameters (depending on shape type)
        -------------------
        time_shift : float
            time (in seconds) between start of event and peak of the shape (only for gaussian and triangle)
        start_shape : float
            time (in seconds) between start of event and start of shape (only for triangle and block)
        end_shape : float
            time (in seconds) between start of event and end of shape (only for triangle and block)
        shape_duration : float
            duration (in seconds) of the shape (only for gaussian)

        Returns
        -------
        np.ndarray
            timeseries of the shape, corresponding to a time_vec with dt=600 seconds
        """
        ...

    @staticmethod
    @abstractmethod
    def read_csv(csvpath: Union[str, Path]) -> pd.DataFrame:
        """read csv file to pandas DataFrame

        Parameters
        ----------
        csvpath : Path
            path to the csv file

        Returns
        -------
        pd.DataFrame
            pandas DataFrame containing the csv data
        """
        ...

    @abstractmethod
    def download_meteo(self, site: ISite, path: Path): ...

    @abstractmethod
    def add_dis_ts(
        self,
        event_dir: Path,
        site_river: list,
        input_river_df_list: Optional[list[pd.DataFrame]] = [],
    ):
        """Creates pd.Dataframe timeseries for river discharge

        Returns
        -------
        self

        """
        ...

    @abstractmethod
    def add_rainfall_ts(self, **kwargs):
        """add timeseries to event for constant or shape-type rainfall, note all relative times and durations are converted to seconds

        Returns
        -------
        self
            updated object with rainfall timeseries added in pd.DataFrame format
        """
        ...

    @abstractmethod
    def add_wind_ts(self):
        """adds constant wind or timeseries from file to event object

        Returns
        -------
        self
            updated object with wind timeseries added in pd.DataFrame format
        """
        ...


class ISynthetic(IEvent):

    attrs: SyntheticModel

    @abstractmethod
    def add_tide_and_surge_ts(self):
        """generating time series of harmoneous tide (cosine) and gaussian surge shape

        Returns
        -------
        self
            updated object with additional attribute of combined tide and surge timeseries as pandas Dataframe
        """
        ...


class IHistoricalNearshore(IEvent):
    
    @abstractmethod
    def download_wl_data(
        station_id: int,
        start_time_str: str,
        stop_time_str: str,
        units: UnitTypesLength,
        file: Union[str, None],
    ) -> pd.DataFrame:
        ...


class IHistoricalOffshore(IEvent):
    ...

class IHistoricalHurricane(IEvent):

    @abstractmethod
    def make_spw_file(self, database_path: Path, model_dir: Path, site=ISite):
        ...

    @abstractmethod
    def translate_tc_track(self, tc: TropicalCyclone, site: ISite):
        ...
