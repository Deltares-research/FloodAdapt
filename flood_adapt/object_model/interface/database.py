import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Union

import pandas as pd
from cht_cyclones.tropical_cyclone import TropicalCyclone
from geopandas import GeoDataFrame

from flood_adapt.object_model.interface.benefits import IBenefit
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.interface.strategies import IStrategy


class IDatabase(ABC):
    input_path: Path
    site: ISite

    @abstractmethod
    def __init__(self, database_path: Union[str, os.PathLike], site_name: str) -> None:
        ...

    @abstractmethod
    def get_aggregation_areas(self) -> dict:
        ...

    @abstractmethod
    def get_property_types(self) -> list:
        ...

    @abstractmethod
    def get_slr_scn_names(self) -> list:
        ...

    @abstractmethod
    def interp_slr(self, slr_scenario: str, year: float) -> float:
        ...

    @abstractmethod
    def plot_slr_scenarios(self) -> str:
        ...

    @abstractmethod
    def plot_wl(self, event: IEvent, input_wl_df: pd.DataFrame = None) -> str:
        ...

    @abstractmethod
    def plot_river(self, event: IEvent) -> str:
        ...

    @abstractmethod
    def plot_rainfall(self, event: IEvent) -> str:
        ...

    @abstractmethod
    def plot_wind(self, event: IEvent) -> str:
        ...

    @abstractmethod
    def get_buildings(self) -> GeoDataFrame:
        ...

    @abstractmethod
    def get_projection(self, name: str) -> IProjection:
        ...

    @abstractmethod
    def save_projection(self, measure: IProjection) -> None:
        ...

    @abstractmethod
    def edit_projection(self, measure: IProjection) -> None:
        ...

    @abstractmethod
    def delete_projection(self, name: str):
        ...

    @abstractmethod
    def copy_projection(self, old_name: str, new_name: str, new_description: str):
        ...

    @abstractmethod
    def get_event(self, name: str) -> IEvent:
        ...

    @abstractmethod
    def save_event(self, measure: IEvent) -> None:
        ...

    @abstractmethod
    def write_to_csv(self, name: str, event: IEvent, df: pd.DataFrame) -> None:
        ...

    @abstractmethod
    def write_cyc(self, event: IEvent, track: TropicalCyclone):
        ...

    @abstractmethod
    def edit_event(self, measure: IEvent) -> None:
        ...

    @abstractmethod
    def delete_event(self, name: str):
        ...

    @abstractmethod
    def copy_event(self, old_name: str, new_name: str, new_description: str):
        ...

    @abstractmethod
    def get_measure(self, name: str) -> IMeasure:
        ...

    @abstractmethod
    def save_measure(self, measure: IMeasure) -> None:
        ...

    @abstractmethod
    def edit_measure(self, measure: IMeasure):
        ...

    @abstractmethod
    def delete_measure(self, name: str):
        ...

    @abstractmethod
    def copy_measure(self, old_name: str, new_name: str, new_description: str):
        ...

    @abstractmethod
    def get_strategy(self, name: str) -> IStrategy:
        ...

    @abstractmethod
    def save_strategy(self, measure: IStrategy) -> None:
        ...

    @abstractmethod
    def delete_strategy(self, name: str):
        ...

    @abstractmethod
    def get_scenario(self, name: str) -> IScenario:
        ...

    @abstractmethod
    def save_scenario(self, measure: IScenario) -> None:
        ...

    @abstractmethod
    def edit_scenario(self, measure: IScenario) -> None:
        ...

    @abstractmethod
    def delete_scenario(self, name: str):
        ...

    @abstractmethod
    def get_benefit(self, name: str) -> IBenefit:
        ...

    @abstractmethod
    def save_benefit(self, benefit: IBenefit) -> None:
        ...

    @abstractmethod
    def edit_benefit(self, measure: IBenefit) -> None:
        ...

    @abstractmethod
    def delete_benefit(self, name: str) -> None:
        ...

    @abstractmethod
    def check_benefit_scenarios(self, benefit: IBenefit) -> None:
        ...

    @abstractmethod
    def create_benefit_scenarios(self, benefit: IBenefit) -> None:
        ...

    @abstractmethod
    def run_benefit(self, benefit_name: Union[str, list[str]]) -> None:
        ...

    @abstractmethod
    def get_projections(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_events(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_measures(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_strategies(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_scenarios(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_benefits(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def get_outputs(self) -> dict[str, Any]:
        ...

    @abstractmethod
    def run_scenario(self, scenario_name: Union[str, list[str]]) -> None:
        ...
