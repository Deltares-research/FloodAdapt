import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

import geopandas as gpd
import numpy as np
import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.config.site import Site
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.dbs_classes.interface.static import IDbsStatic
from flood_adapt.objects.benefits.benefits import Benefit
from flood_adapt.objects.events.events import Event


class IDatabase(ABC):
    base_path: Path
    input_path: Path
    output_path: Path
    static_path: Path

    @property
    @abstractmethod
    def site(self) -> Site: ...

    @property
    @abstractmethod
    def static(self) -> IDbsStatic: ...

    @property
    @abstractmethod
    def events(self) -> AbstractDatabaseElement: ...

    @property
    @abstractmethod
    def scenarios(self) -> AbstractDatabaseElement: ...

    @property
    @abstractmethod
    def strategies(self) -> AbstractDatabaseElement: ...

    @property
    @abstractmethod
    def measures(self) -> AbstractDatabaseElement: ...

    @property
    @abstractmethod
    def projections(self) -> AbstractDatabaseElement: ...

    @property
    @abstractmethod
    def benefits(self) -> AbstractDatabaseElement: ...

    @abstractmethod
    def __init__(
        self, database_path: Union[str, os.PathLike], site_name: str
    ) -> None: ...

    @abstractmethod
    def interp_slr(self, slr_scenario: str, year: float) -> float:
        pass

    @abstractmethod
    def plot_slr_scenarios(self) -> str:
        pass

    @abstractmethod
    def write_to_csv(self, name: str, event: Event, df: pd.DataFrame) -> None:
        pass

    @abstractmethod
    def write_cyc(self, event: Event, track: TropicalCyclone) -> None:
        pass

    @abstractmethod
    def check_benefit_scenarios(self, benefit: Benefit) -> pd.DataFrame:
        pass

    @abstractmethod
    def create_benefit_scenarios(self, benefit: Benefit) -> None:
        pass

    @abstractmethod
    def run_benefit(self, benefit_name: Union[str, list[str]]) -> None:
        pass

    @abstractmethod
    def get_outputs(self) -> dict[str, Any]:
        pass

    @abstractmethod
    def get_topobathy_path(self) -> str:
        pass

    @abstractmethod
    def get_index_path(self) -> str:
        pass

    @abstractmethod
    def get_depth_conversion(self) -> float:
        pass

    @abstractmethod
    def get_max_water_level(
        self, scenario_name: str, return_period: Optional[int] = None
    ) -> np.ndarray:
        pass

    @abstractmethod
    def get_building_footprints(self, scenario_name: str) -> gpd.GeoDataFrame:
        pass

    @abstractmethod
    def get_roads(self, scenario_name: str) -> gpd.GeoDataFrame:
        pass

    @abstractmethod
    def get_aggregation(self, scenario_name: str) -> dict[str, gpd.GeoDataFrame]:
        pass

    @abstractmethod
    def get_aggregation_benefits(
        self, benefit_name: str
    ) -> dict[str, gpd.GeoDataFrame]:
        pass

    @abstractmethod
    def get_object_list(self, object_type: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def has_run_hazard(self, scenario_name: str) -> None:
        pass

    @abstractmethod
    def cleanup(self) -> None:
        pass
