from pathlib import Path
from typing import Any

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
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
        measures = super().summarize_objects()
        objects = self.list_all()

        geometries = []
        for obj in objects:
            if obj.polygon_file:
                geom = obj.read_gdf()
            elif obj.aggregation_area_name and obj.aggregation_area_type:
                geom = self._database.static.get_aggregation_area_by_type_and_name(
                    obj.aggregation_area_type, obj.aggregation_area_name
                )
            else:
                geom = None
            geometries.append(geom)

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
