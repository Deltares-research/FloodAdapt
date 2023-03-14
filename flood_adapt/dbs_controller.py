import os
import shutil
from datetime import datetime
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Union

import geopandas as gpd
from geopandas import GeoDataFrame

from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.database import IDatabase
from flood_adapt.object_model.interface.events import IEvent
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import ISite
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.io.fiat import Fiat
from flood_adapt.object_model.measure_factory import MeasureFactory
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.scenario import Scenario
from flood_adapt.object_model.site import Site
from flood_adapt.object_model.strategy import Strategy


class Database(IDatabase):
    input_path: Path
    site: ISite
    events: list[IEvent]
    projections: list[IProjection]
    measures: list[IMeasure]
    strategies: list[IStrategy]
    scenarios: list[IScenario]
    fiat_model: Fiat

    def __init__(self, database_path: Union[str, os.PathLike], site_name: str) -> None:
        self.input_path = Path(database_path) / site_name / "input"
        self.site = Site.load_file(
            Path(database_path) / site_name / "static" / "site" / "site.toml"
        )
        # self.update()

    # General methods
    def get_aggregation_areas(self) -> list[GeoDataFrame]:
        aggregation_areas = [
            gpd.read_file(
                self.input_path.parent / "static" / "site" / aggr_dict.file
            ).to_crs(4326)
            for aggr_dict in self.site.attrs.fiat.aggregation
        ]
        # Make sure they are ordered alphabetically
        aggregation_areas = [
            aggregation_areas.sort_values(
                by=self.site.attrs.fiat.aggregation[i].field_name
            ).reset_index(drop=True)
            for i, aggregation_areas in enumerate(aggregation_areas)
        ]
        return aggregation_areas

    def get_buildings(self) -> GeoDataFrame:
        fiat_model = Fiat(
            fiat_path=self.input_path.parent / "static" / "templates" / "fiat",
            crs=self.site.attrs.fiat.exposure_crs,
        )
        buildings = fiat_model.get_buildings(
            type="ALL", non_building_names=self.site.attrs.fiat.non_building_names
        )
        return buildings

    # Measure methods
    def get_measure(self, name: str) -> IMeasure:
        measure_path = self.input_path / "measures" / name / f"{name}.toml"
        measure = MeasureFactory.get_measure_object(measure_path)
        return measure

    def save_measure(self, measure: IMeasure) -> None:
        names = self.get_measures()["name"]
        if measure.attrs.name in names:
            raise ValueError(
                f"'{measure.attrs.name}' name is already used by another measure. Choose a different name"
            )
        else:
            (self.input_path / "measures" / measure.attrs.name).mkdir()
            measure.save(
                self.input_path
                / "measures"
                / measure.attrs.name
                / f"{measure.attrs.name}.toml"
            )

    def edit_measure(self, measure: IMeasure):
        # TODO should you be able to edit a measure that is already used in a strategy?
        measure.save(
            self.input_path
            / "measures"
            / measure.attrs.name
            / f"{measure.attrs.name}.toml"
        )

    def delete_measure(self, name: str):
        # TODO check strategies that use a measure
        # used_strategy = [
        #     name in measures
        #     for measures in [strategy.attrs.measures for strategy in self.strategies]
        # ]
        # if any(used_strategy):
        #     strategies = [
        #         strategy.attrs.name
        #         for i, strategy in enumerate(self.strategies)
        #         if used_strategy[i]
        #     ]
        #     text = "strategy" if len(strategies) == 1 else "strategies"
        #     raise ValueError(
        #         f"'{name}' measure cannot be deleted since it is already used in {text} {strategies}"
        #     )
        # else:
        measure_path = self.input_path / "measures" / name
        shutil.rmtree(measure_path, ignore_errors=True)

    def copy_measure(self, old_name: str, new_name: str, new_long_name: str):
        old_measure_path = self.input_path / "measures" / old_name
        new_measure_path = self.input_path / "measures" / new_name
        copy_tree(str(old_measure_path), str(new_measure_path))
        # TODO change names of files and toml attributes

    def update(self) -> None:
        self.projections = self.get_projections()
        self.events = self.get_events()
        self.measures = self.get_measures()
        self.strategies = self.get_strategies()
        self.scenarios = self.get_scenarios()

    def get_projections(self):
        projections = self.get_object_list(object_type="Projections")
        objects = [Projection.load_file(path) for path in projections["path"]]
        projections["name"] = [obj.attrs.name for obj in objects]
        projections["long_name"] = [obj.attrs.long_name for obj in objects]
        return projections

    def get_events(self):
        events = self.get_object_list(object_type="Events")
        objects = [Hazard.get_event_object(path) for path in events["path"]]
        events["name"] = [obj.attrs.name for obj in objects]
        events["long_name"] = [obj.attrs.long_name for obj in objects]
        return events

    def get_measures(self):
        measures = self.get_object_list(object_type="Measures")
        objects = [MeasureFactory.get_measure_object(path) for path in measures["path"]]
        measures["name"] = [obj.attrs.name for obj in objects]
        measures["long_name"] = [obj.attrs.long_name for obj in objects]
        measures["geometry"] = [
            gpd.read_file(path.parent.joinpath(obj.attrs.polygon_file))
            if obj.attrs.polygon_file is not None
            else None
            for (path, obj) in zip(measures["path"], objects)
        ]
        return measures

    def get_strategies(self):
        strategies = self.get_object_list(object_type="Strategies")
        objects = [Strategy.load_file(path) for path in strategies["path"]]
        strategies["name"] = [obj.attrs.name for obj in objects]
        strategies["long_name"] = [obj.attrs.long_name for obj in objects]
        return strategies

    def get_scenarios(self):
        scenarios = self.get_object_list(object_type="Scenarios")
        objects = [Scenario.load_file(path) for path in scenarios["path"]]
        scenarios["name"] = [obj.attrs.name for obj in objects]
        scenarios["long_name"] = [obj.attrs.long_name for obj in objects]
        return scenarios

    def get_object_list(self, object_type: str):
        paths = [
            path / f"{path.name}.toml"
            for path in list((self.input_path / object_type).iterdir())
        ]
        last_modification_date = [
            datetime.fromtimestamp(file.stat().st_mtime) for file in paths
        ]

        objects = {
            "path": paths,
            "last_modification_date": last_modification_date,
        }

        return objects
