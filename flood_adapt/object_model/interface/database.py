import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.dbs_classes.dbs_interface import AbstractDatabaseElement
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.object_model.hazard.interface.events import IEvent
from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.site import Site


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
    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame) -> None: ...

    @abstractmethod
    def write_cyc(self, event: IEvent, track: TropicalCyclone): ...

    @abstractmethod
    def check_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def create_benefit_scenarios(self, benefit: IBenefit) -> None: ...

    @abstractmethod
    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None: ...
