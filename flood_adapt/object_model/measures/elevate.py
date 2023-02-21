from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.measures.measure import Measure

class Elevate(Measure):
    def __init__(self, config_file: str = None):
        super().__init__(config_file)

    def set_default(self):
        super().set_default()
        self.elevation = {}
        self.elevation["value"] = None
        self.elevation["units"] = "m"
        self.elevation["type"] = "floodmap"
        self.selection_type = None 
        self.aggregation_area = None  # this is needed if selection type is aggregation_area
        self.polygon_file = None # this is needed if selection type is polygon
        self.property_type = 'RES'
        self.datum = None

    def set_elevation(self, elevation: dict):
        self.elevation["value"] = elevation["value"]
        self.elevation["units"] = elevation["units"]
        self.elevation["type"] = elevation["type"]

    def set_selection_type(self, selection_type):
        self.selection_type = selection_type

    def set_aggregation_area(self, aggregation_area):
        self.aggregation_area = aggregation_area

    def set_polygon_file(self, polygon_file):
        self.polygon_file = polygon_file

    def set_property_type(self, property_type):
        self.property_type = property_type

    def set_datum(self, datum):
        self.datum = datum

    def load(self):
        super().load()
        if self.config_file:
            if isinstance(self.config_file, str):
                config = read_config(self.config_file)
                self.set_elevation(config["elevation"])
                self.set_selection_type(config["selection_type"])
                if self.selection_type == "aggregation_area":
                    self.set_aggregation_area(config["aggregation_area"])
                elif self.selection_type == "polygon":
                    self.set_polygon_file(config["polygon_file"])
                self.set_property_type(config["property_type"])
                self.set_datum(config["datum"])
