import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

import geopandas as gpd
import numpy as np

from flood_adapt.config import Site
from flood_adapt.dbs_classes.dbs_static import IDbsStatic
from flood_adapt.dbs_classes.interface.element import AbstractDatabaseElement


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
        self, database_path: Union[str, os.PathLike], site_name: str
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
    def get_object_list(self, object_type: str) -> dict[str, Any]: ...

    @abstractmethod
    def has_run_hazard(self, scenario_name: str) -> None: ...

    @abstractmethod
    def cleanup(self) -> None: ...
