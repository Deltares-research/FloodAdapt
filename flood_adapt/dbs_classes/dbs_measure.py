from pathlib import Path
from typing import Any

import geopandas as gpd

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.exceptions import DatabaseError
from flood_adapt.misc.utils import resolve_filepath
from flood_adapt.objects.measures.measure_factory import MeasureFactory
from flood_adapt.objects.measures.measures import Measure


class DbsMeasure(DbsTemplate[Measure]):
    dir_name = "measures"
    display_name = "Measure"
    _object_class = Measure
    _higher_lvl_object = "Strategy"

    def _read_object(self, path: Path):
        return MeasureFactory.get_measure_object(path)

    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the measures that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' and 'geometry' info
        """
        measures = self._get_object_summary()
        objects = self.list_all()

        geometries = []
        # TODO move reading geo data to Measure.load_file or obj.read() and use that data here.
        for obj in objects:
            # If polygon is used read the polygon file
            if hasattr(obj, "polygon_file") and obj.polygon_file:
                src_path = resolve_filepath(
                    object_dir=self.dir_name,
                    obj_name=obj.name,
                    path=obj.polygon_file,
                )
                geometries.append(gpd.read_file(src_path))
            # If aggregation area is used read the polygon from the aggregation area name
            elif hasattr(obj, "aggregation_area_name") and obj.aggregation_area_name:
                if (
                    obj.aggregation_area_type
                    not in self._database.static.get_aggregation_areas()
                ):
                    raise DatabaseError(
                        f"Aggregation area type {obj.aggregation_area_type} for measure {obj.name} does not exist."
                    )
                gdf = self._database.static.get_aggregation_areas()[
                    obj.aggregation_area_type
                ]
                if obj.aggregation_area_name not in gdf["name"].to_numpy():
                    raise DatabaseError(
                        f"Aggregation area name {obj.aggregation_area_name} for measure {obj.name} does not exist."
                    )
                geometries.append(gdf.loc[gdf["name"] == obj.aggregation_area_name, :])
            # Else assign a None value
            else:
                geometries.append(None)

        measures["geometry"] = geometries
        return measures

    def used_by_higher_level(self, name: str) -> list[str]:
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
        strategies = self._database.strategies.list_all()

        # Check if measure is used in a strategy
        used_in_strategy = [
            strategy.name
            for strategy in strategies
            for measure in strategy.measures
            if name == measure
        ]
        return used_in_strategy
