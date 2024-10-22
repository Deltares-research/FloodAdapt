import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.config import Settings
from flood_adapt.dbs_classes.dbs_template import AbstractDatabaseElement
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.site import Site


class TopLevelDir(str, Enum):
    """Top level directories in the database."""

    input = "input"
    output = "output"
    static = "static"
    temp = "temp"


class ObjectDir(str, Enum):
    """The names for object directories at the second level of the database."""

    site = "site"

    benefit = "benefits"
    event = "events"
    strategy = "strategies"
    measure = "measures"
    projection = "projections"
    scenario = "scenarios"

    buyout = "measures"
    elevate = "measures"
    floodproof = "measures"
    greening = "measures"
    floodwall = "measures"
    pump = "measures"


def db_path(
    top_level_dir: TopLevelDir = TopLevelDir.input,
    object_dir: Optional[ObjectDir] = None,
    obj_name: Optional[str] = None,
) -> Path:
    """Return an path to a database directory from arguments."""
    rel_path = Path(top_level_dir.value)
    if object_dir is not None:
        if isinstance(object_dir, ObjectDir):
            rel_path = rel_path / object_dir.value
        else:
            rel_path = rel_path / str(object_dir)

        if obj_name is not None:
            rel_path = rel_path / obj_name

    return Settings().database_path / rel_path


class IDatabase(ABC):
    base_path: Path
    input_path: Path
    output_path: Path
    static_path: Path

    static_sfincs_model: SfincsAdapter

    @property
    @abstractmethod
    def site(self) -> Site: ...

    @property
    @abstractmethod
    def static(self) -> AbstractDatabaseElement: ...

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
    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame) -> None: ...

    @abstractmethod
    def write_cyc(self, event: IEvent, track: TropicalCyclone): ...

    @abstractmethod
    def check_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def create_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None: ...
