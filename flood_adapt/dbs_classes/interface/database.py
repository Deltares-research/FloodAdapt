import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import numpy as np

from flood_adapt.config.config import Settings
from flood_adapt.config.site import Site
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.dbs_classes.interface.static import IDbsStatic


class IDatabase(ABC):
    base_path: Path
    input_path: Path
    output_path: Path
    static_path: Path

    site: Site
    static: IDbsStatic

    events: AbstractDatabaseElement
    scenarios: AbstractDatabaseElement
    strategies: AbstractDatabaseElement
    measures: AbstractDatabaseElement
    projections: AbstractDatabaseElement
    benefits: AbstractDatabaseElement

    @abstractmethod
    def __init__(
        self,
        database_path: str | os.PathLike | None = None,
        database_name: str | None = None,
        settings: Settings | None = None,
    ) -> None: ...

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
