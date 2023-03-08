from pathlib import Path

import geopandas as gpd

from flood_adapt.object_model.measure import Measure
from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.io.fiat_data import FiatModel
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)

class ImpactMeasure(Measure):
    """ImpactMeasure class that holds all the information for a specific measure type that affects the impact model"""

    def set_default(self) -> None:
        """Sets the default values"""
        super().set_default()
        self.selection_type = None  # selection type (can be "aggregation area", "all" or "polygon")
        self.aggregation_area = None  # name of area to use (this is needed if selection type is "aggregation_area")
        self.polygon_file = None  # polygon file to use (this is needed if selection type is "polygon")
        self.property_type = "RES"  # this is the object type to be used to apply the measure on
        self.mandatory_keys.extend(["selection_type"])

    @property
    def selection_type(self):
        return self._selection_type

    @selection_type.setter
    def selection_type(self, value: str):
        self._selection_type = value

    @property
    def aggregation_area(self):
        return self._aggregation_area

    @aggregation_area.setter
    def aggregation_area(self, value: str):
        self._aggregation_area = value
  
    @property
    def polygon_file(self):
        return self._polygon_file

    @polygon_file.setter
    def polygon_file(self, value: str):
        self._polygon_file = value
 
    @property
    def property_type(self):
        return self._property_type

    @property_type.setter
    def property_type(self, value: str):
        self._property_type = value

    def load(self, config_file: str = None):
        """loads and updates the class attributes from a configuration file"""
        super().load(config_file)
        self.selection_type = self._config["selection_type"]
        if (
            self.selection_type == "aggregation_area"
            and validate_content_config_file(
                self._config, self.config_file, ["aggregation_area"]
            )
        ):
            self.aggregation_area = self._config["aggregation_area"]
        elif self.selection_type == "polygon" and validate_content_config_file(
            self._config, self.config_file, ["polygon_file"]
        ):
            self.polygon_file = self._config["polygon_file"]

        self.property_type = self._config["property_type"]

    def get_object_ids(self):
        """Get ids of objects that are affected by the measure"""
        database = DatabaseIO()  # this is needed to get to the FIAT model path
        buildings = FiatModel(database.database_path).get_buildings(self.property_type)

        if (self.selection_type == "aggregation_area") | (self.selection_type == "all"):
            if self.selection_type == "all":
                ids = buildings["Object ID"].to_numpy()
            elif self.selection_type == "aggregation_area":
                ids = buildings.loc[
                    buildings["Aggregation Label: subdivision"]
                    == self.aggregation_area,
                    "Object ID",
                ].to_numpy()  # TODO: aggregation label should be read from site config
        elif self.selection_type == "polygon":
            polygon = gpd.read_file(Path(self.config_file).parent / self.polygon_file)
            ids = gpd.sjoin(buildings, polygon)["Object ID"].to_numpy()

        return list(ids)
