from typing import Any

import geopandas as gpd

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.object_model.interface.measures import Measure
from flood_adapt.object_model.measure_factory import MeasureFactory
from flood_adapt.object_model.utils import resolve_filepath


class DbsMeasure(DbsTemplate[Measure]):
    dir_name = "measures"
    display_name = "Measure"
    _object_class = Measure

    def get(self, name: str) -> Measure:
        """Return a measure object.

        Parameters
        ----------
        name : str
            name of the measure to be returned

        Returns
        -------
        Measure
            measure object
        """
        measure_path = self.input_path / name / f"{name}.toml"
        measure = MeasureFactory.get_measure_object(measure_path)
        return measure

    def list_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the measures that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        measures = self._get_object_list()
        objects = [MeasureFactory.get_measure_object(path) for path in measures["path"]]
        measures["description"] = [obj.description for obj in objects]
        measures["objects"] = objects

        geometries = []
        for path, obj in zip(measures["path"], objects):
            # If polygon is used read the polygon file
            if obj.polygon_file:
                src_path = resolve_filepath(
                    object_dir=self.dir_name,
                    obj_name=obj.name,
                    path=obj.polygon_file,
                )
                geometries.append(gpd.read_file(src_path))
            # If aggregation area is used read the polygon from the aggregation area name
            elif obj.aggregation_area_name:
                if (
                    obj.aggregation_area_type
                    not in self._database.static.get_aggregation_areas()
                ):
                    raise ValueError(
                        f"Aggregation area type {obj.aggregation_area_type} for measure {obj.name} does not exist."
                    )
                gdf = self._database.static.get_aggregation_areas()[
                    obj.aggregation_area_type
                ]
                if obj.aggregation_area_name not in gdf["name"].to_numpy():
                    raise ValueError(
                        f"Aggregation area name {obj.aggregation_area_name} for measure {obj.name} does not exist."
                    )
                geometries.append(gdf.loc[gdf["name"] == obj.aggregation_area_name, :])
            # Else assign a None value
            else:
                geometries.append(None)

        measures["geometry"] = geometries
        return measures

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Check if a measure is used in a strategy.

        Parameters
        ----------
        name : str
            name of the measure to be checked

        Returns
        -------
        list[str]
            list of strategies that use the measure
        """
        # Get all the strategies
        strategies = self._database.strategies.list_objects()["objects"]

        # Check if measure is used in a strategy
        used_in_strategy = [
            strategy.name
            for strategy in strategies
            for measure in strategy.measures
            if name == measure
        ]
        return used_in_strategy
