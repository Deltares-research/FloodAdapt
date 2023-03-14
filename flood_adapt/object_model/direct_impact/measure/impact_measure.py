import os
from abc import ABC
from pathlib import Path
from typing import Any, Union

import geopandas as gpd

from flood_adapt.object_model.interface.measures import ImpactMeasureModel
from flood_adapt.object_model.io.fiat import Fiat
from flood_adapt.object_model.site import Site


class ImpactMeasure(ABC):
    """ImpactMeasure class that holds all the information for a
    specific measure type that affects the impact model."""

    attrs: ImpactMeasureModel
    database_input_path: Union[str, os.PathLike]

    def get_object_ids(self) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        site = Site.load_file(
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )
        buildings = Fiat(
            Path(self.database_input_path).parent / "static" / "templates" / "fiat"
        ).get_buildings(
            self.attrs.property_type,
            non_building_names=site.attrs.fiat.non_building_names,
        )

        if (self.attrs.selection_type == "aggregation_area") or (
            self.attrs.selection_type == "all"
        ):
            if self.attrs.selection_type == "all":
                ids = buildings["Object ID"].to_numpy()
            elif self.attrs.selection_type == "aggregation_area":
                label = site.attrs.fiat.aggregation[
                    0
                ].name  # Alwats use first aggregation area type
                ids = buildings.loc[
                    buildings[f"Aggregation Label: {label}"]
                    == self.attrs.aggregation_area_name,
                    "Object ID",
                ].to_numpy()
        elif self.attrs.selection_type == "polygon":
            assert self.attrs.polygon_file is not None
            polygon = gpd.read_file(
                Path(self.database_input_path)
                / "measures"
                / self.attrs.name
                / self.attrs.polygon_file
            )
            ids = gpd.sjoin(buildings, polygon)["Object ID"].to_numpy()

        return list(ids)
