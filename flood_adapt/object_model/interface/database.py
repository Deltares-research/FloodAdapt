import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone
from geopandas import GeoDataFrame

from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.site import ISite


class IDatabase(ABC):
    input_path: Path
    output_path: Path
    static_path = Path
    site: ISite

    @abstractmethod
    def __init__(
        self, database_path: Union[str, os.PathLike], site_name: str
    ) -> None: ...

    @abstractmethod
    def get_aggregation_areas(self) -> dict: ...

    @abstractmethod
    def get_model_boundary(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_obs_points(self) -> GeoDataFrame: ...

    @abstractmethod
    def get_property_types(self) -> list: ...

    @abstractmethod
    def get_slr_scn_names(self) -> list: ...

    @abstractmethod
    def interp_slr(self, slr_scenario: str, year: float) -> float: ...

    @abstractmethod
    def plot_slr_scenarios(self) -> str: ...

    @abstractmethod
    def plot_wl(self, event: IEvent, input_wl_df: pd.DataFrame = None) -> str: ...

    @abstractmethod
    def plot_river(self, event: IEvent, input_river_df: list[pd.DataFrame]) -> str: ...

    @abstractmethod
    def plot_rainfall(
        self, event: IEvent, input_rainfall_df: pd.DataFrame = None
    ) -> str: ...

    @abstractmethod
    def plot_wind(self, event: IEvent, input_wind_df: pd.DataFrame = None) -> str: ...

    @abstractmethod
    def get_buildings(self) -> GeoDataFrame: ...

    @abstractmethod
    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame) -> None: ...

    @abstractmethod
    def write_cyc(self, event: IEvent, track: TropicalCyclone): ...

    @abstractmethod
    def check_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def create_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None: ...
