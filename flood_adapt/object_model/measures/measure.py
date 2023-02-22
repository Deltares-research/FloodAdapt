from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.io.fiat_data import FiatModel
from flood_adapt.object_model.validate.config import validate_existence_config_file, validate_content_config_file
from pathlib import Path
import pandas as pd
import geopandas as gpd
class Measure:
    """ Measure class that holds all the information for a specific measure type
    """
    def __init__(self, config_file: str = None, database_path: str = None) -> None:
        self.set_default()
        self.database_path = database_path
        if config_file:
            self.config_file = config_file
            if not self.database_path:
                self.database_path = str(Path(self.config_file).parents[3])

    def set_default(self):
        """ Sets the default values of the Measure class attributes
        """
        self.name = ""  # Name of the measure
        self.long_name = ""  # Long name of the measure
        self.config_file = None  # path to the configuration file connected with the measure
        self.type = ""  # type of the measure
        self.mandatory_keys = ["name", "long_name"]  # mandatory keys in the config file

    def set_name(self, name: str):
        self.name = name
    
    def set_long_name(self, long_name: str):
        self.long_name = long_name

    def load(self):
        """ loads and updates the class attributes from a configuration file
        """
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            config = read_config(self.config_file)

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(config, self.config_file, self.mandatory_keys):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])

    def get_object_ids(self):
        """ Get ids of objects that are affected by the measure
        """
        
        buildings = FiatModel(self.database_path).get_buildings(self.property_type)

        if (self.selection_type == "aggregation_area") | (self.selection_type == "all"):
            if self.selection_type == "all":
                ids = buildings['Object ID'].values
            elif self.selection_type == "aggregation_area":
                ids =  buildings.loc[buildings["Aggregation Label: subdivision"] == self.aggregation_area, 'Object ID'].values  # TODO: aggregation label should be read from site config
        elif self.selection_type == "polygon":
            polygon = gpd.read_file(Path(self.config_file).parent / self.polygon_file)
            ids = gpd.sjoin(buildings, polygon)['Object ID'].values
            buildings.to_file('buildings.shp')
            polygon.to_file('polygon.shp')

        return list(ids)

