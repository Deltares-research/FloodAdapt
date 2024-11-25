from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

import geopandas as gpd
import pandas as pd

from flood_adapt.integrator.sfincs_adapter import SfincsAdapter


class IDbsStatic(ABC):
    @abstractmethod
    def get_static_sfincs_model(self) -> SfincsAdapter: ...

    @abstractmethod
    def get_aggregation_areas(self) -> dict: ...

    @abstractmethod
    def get_model_boundary(self) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def get_model_grid(self): ...

    @abstractmethod
    def get_obs_points(self) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def get_static_map(self, path: Union[str, Path]) -> gpd.gpd.GeoDataFrame: ...

    @abstractmethod
    def get_slr_scn_names(self) -> list: ...

    @abstractmethod
    def get_green_infra_table(self, measure_type: str) -> pd.DataFrame: ...

    @abstractmethod
    def get_buildings(self) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def get_property_types(self) -> list: ...
