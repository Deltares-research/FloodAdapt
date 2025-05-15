from pathlib import Path
from typing import Any

import geopandas as gpd

from flood_adapt.dbs_classes.dbs_template import DbsTemplate
from flood_adapt.misc.utils import resolve_filepath
from flood_adapt.objects.measures.measure_factory import MeasureFactory
from flood_adapt.objects.measures.measures import Measure


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
        # Make the full path to the object
        full_path = self.input_path / name / f"{name}.toml"

        # Check if the object exists
        if not Path(full_path).is_file():
            raise ValueError(f"{self.display_name}: '{name}' does not exist.")

        # Load and return the object
        return MeasureFactory.get_measure_object(full_path)

    def summarize_objects(self) -> dict[str, list[Any]]:
        """Return a dictionary with info on the measures that currently exist in the database.

        Returns
        -------
        dict[str, Any]
            Includes 'name', 'description', 'path' and 'last_modification_date' and 'geometry' info
        """
        measures = self._get_object_summary()
        objects = [self.get(name) for name in measures["name"]]

        geometries = []
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
        strategies = [
            self._database.strategies.get(strategy)
            for strategy in self._database.strategies.summarize_objects()["name"]
        ]

        # Check if measure is used in a strategy
        used_in_strategy = [
            strategy.name
            for strategy in strategies
            for measure in strategy.measures
            if name == measure
        ]
        return used_in_strategy
