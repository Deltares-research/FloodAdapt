import os
from typing import Any

import geopandas as gpd

from flood_adapt.dbs_classes.dbs_object import DbsObject
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.object_classes.measure.measure import Measure
from flood_adapt.object_model.object_classes.measure.measure_factory import (
    MeasureFactory,
)


class DbsMeasure(DbsObject):
    _type = "measure"
    _folder_name = "measures"
    _object_model_class = Measure

    def get(self, name: str) -> IMeasure:
        """Returns a measure object.

        Parameters
        ----------
        name : str
            name of the measure to be returned

        Returns
        -------
        IMeasure
            measure object
        """
        obj, data = super().get(name, get_data=True)  # Return object of type Measure
        measure = MeasureFactory.get_sub_measure(obj, data)
        return measure

    def list_objects(self) -> dict[str, Any]:
        """Returns a dictionary with info on the measures that currently
        exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' info
        """
        measures = self._get_object_list()
        objects = [self.get(os.path.basename(path)) for path in measures["path"]]
        measures["name"] = [obj.attrs.name for obj in objects]
        measures["description"] = [obj.attrs.description for obj in objects]
        measures["objects"] = objects

        geometries = []
        for path, obj in zip(measures["path"], objects):
            # If polygon is used read the polygon file
            if obj.attrs.polygon_file:
                file_path = path.parent.joinpath(obj.attrs.polygon_file)
                if not file_path.exists():
                    raise FileNotFoundError(
                        f"Polygon file {obj.attrs.polygon_file} for measure {obj.attrs.name} does not exist."
                    )
                geometries.append(gpd.read_file(file_path))
            # If aggregation area is used read the polygon from the aggregation area name
            elif obj.attrs.aggregation_area_name:
                if obj.attrs.aggregation_area_type not in self._database.aggr_areas:
                    raise ValueError(
                        f"Aggregation area type {obj.attrs.aggregation_area_type} for measure {obj.attrs.name} does not exist."
                    )
                gdf = self._database.aggr_areas[obj.attrs.aggregation_area_type]
                if obj.attrs.aggregation_area_name not in gdf["name"].to_numpy():
                    raise ValueError(
                        f"Aggregation area name {obj.attrs.aggregation_area_name} for measure {obj.attrs.name} does not exist."
                    )
                geometries.append(
                    gdf.loc[gdf["name"] == obj.attrs.aggregation_area_name, :]
                )
            # Else assign a None value
            else:
                geometries.append(None)

        measures["geometry"] = geometries
        return measures

    def check_higher_level_usage(self, name: str) -> list[str]:
        """Checks if a measure is used in a strategy.

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
        strategies = [
            self._database.strategies.get(os.path.basename(path))
            for path in self._database.strategies.list_objects()["path"]
        ]

        # Check if measure is used in a strategy
        used_in_strategy = [
            strategy.attrs.name
            for strategy in strategies
            for measure in strategy.attrs.measures
            if name == measure
        ]
        return used_in_strategy
