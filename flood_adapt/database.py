import os
from pathlib import Path
from typing import Union

from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.measure_factory import MeasureFactory
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy


class DatabaseController:
    site: ISite
    events: list[IEvent]
    projections: list[IProjection]
    measures: list[IMeasure]
    strategies: list[IStrategy]
    scenarios: list[IScenario]

    def __init__(self, database_path: Union[str, os.PathLike], site_name: str) -> None:
        self.input_path = Path(database_path) / site_name / "input"
        self.site = Site.load_file(
            Path(database_path) / site_name / "static" / "site" / f"{site_name}.toml"
        )
        self.update()

    def update(self) -> None:
        """Updates the database with the actual toml files that exist"""
        self.projections = [
            Projection.load_file(path) for path in self.get_object_paths("projections")
        ]

        self.events = [
            Hazard.get_event_object(path) for path in self.get_object_paths("events")
        ]

        self.measures = [
            MeasureFactory.get_measure_object(path)
            for path in self.get_object_paths("measures")
        ]

        self.strategies = [
            Strategy.load_file(path) for path in self.get_object_paths("strategies")
        ]

        self.scenarios = [
            Scenario.load_file(path) for path in self.get_object_paths("scenarios")
        ]

    def get_object_paths(self, object_type: str) -> list[Path]:
        """Given a specific type of objects, gets all paths of the toml config files
        that exist in the database.

        Parameters
        ----------
        object_type : str
            type of object (can be 'projections', 'events', 'measures', 'strategies' or 'scenarios')

        Returns
        -------
        list[Path]
            list of toml config paths for the specific type of objects
        """
        object_paths = [
            path / f"{path.name}.toml"
            for path in list((self.input_path / object_type).iterdir())
        ]
        return object_paths
