from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import geopandas as gpd
import numpy as np

from flood_adapt.config.database import DatabaseConfig, PostProcessingFunction
from flood_adapt.config.settings import Settings
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement
from flood_adapt.dbs_classes.interface.static import IDbsStatic


class IDatabase(ABC):
    base_path: Path
    input_path: Path
    output_path: Path
    static_path: Path

    config: DatabaseConfig

    static: IDbsStatic
    events: AbstractDatabaseElement
    scenarios: AbstractDatabaseElement
    strategies: AbstractDatabaseElement
    measures: AbstractDatabaseElement
    projections: AbstractDatabaseElement
    benefits: AbstractDatabaseElement

    _settings: Settings

    @abstractmethod
    def __init__(
        self,
        database_root: Path | None,
        database_name: str | None,
        settings: Settings | None = None,
    ) -> None: ...

    @abstractmethod
    def read_site(self, site_name: str) -> None: ...

    @abstractmethod
    def get_outputs(self) -> dict[str, Any]: ...

    @abstractmethod
    def get_topobathy_path(self) -> str: ...

    @abstractmethod
    def get_index_path(self) -> str: ...

    @abstractmethod
    def get_depth_conversion(self) -> float: ...

    @abstractmethod
    def get_max_water_level(
        self, scenario_name: str, return_period: Optional[int] = None
    ) -> np.ndarray: ...

    @abstractmethod
    def get_building_footprints(self, scenario_name: str) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def get_roads(self, scenario_name: str) -> gpd.GeoDataFrame: ...

    @abstractmethod
    def get_aggregation(self, scenario_name: str) -> dict[str, gpd.GeoDataFrame]: ...

    @abstractmethod
    def get_aggregation_benefits(
        self, benefit_name: str
    ) -> dict[str, gpd.GeoDataFrame]: ...

    @abstractmethod
    def has_run_hazard(self, scenario_name: str) -> None: ...

    @abstractmethod
    def get_postprocessing_hooks(
        self, reload: bool = False
    ) -> dict[str, PostProcessingFunction] | None: ...

    @abstractmethod
    def cleanup(self) -> None: ...
