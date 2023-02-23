from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import validate_existence_config_file, validate_content_config_file
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure

class Elevate(ImpactMeasure):
    """ Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height
    """
    def __init__(self) -> None:
        super().__init__()

    def set_default(self):
        """ Sets the default values of the Elevate class attributes
        """
        super().set_default()
        self.type = "elevate_properties"  # name reference that is used to know which class to use when the config file is read
        self.elevation = {}
        self.elevation["value"] = None  # the height to elevate the properties by
        self.elevation["units"] = "m"  # the units that the height is given
        self.elevation["type"] = "floodmap"  # type of height reference (can be "floodmap" or "datum")
        self.selection_type = None   # selection type (can be "aggregation area", "all" or "polygon")
        self.aggregation_area = None  # name of area to use (this is needed if selection type is "aggregation_area")
        self.polygon_file = None  # polygon file to use (this is needed if selection type is "polygon")
        self.property_type = "RES"  # this is the object type to be used to apply the measure on 
        self.mandatory_keys.extend(["elevation", "selection_type"])

    def set_elevation(self, elevation: dict):
        self.elevation["value"] = elevation["value"]
        self.elevation["units"] = elevation["units"]
        self.elevation["type"] = elevation["type"]

    def set_selection_type(self, selection_type:str):
        self.selection_type = selection_type

    def set_aggregation_area(self, aggregation_area):
        self.aggregation_area = aggregation_area

    def set_polygon_file(self, polygon_file):
        self.polygon_file = polygon_file

    def set_property_type(self, property_type):
        self.property_type = property_type

    def load(self,  config_file: str = None):
        """ loads and updates the class attributes from a configuration file
        """
        super().load(config_file)
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            config = read_config(self.config_file)

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(config, self.config_file, self.mandatory_keys):
            self.set_elevation(config["elevation"])
            self.set_selection_type(config["selection_type"])

            if self.selection_type == "aggregation_area" and validate_content_config_file(config, self.config_file, ["aggregation_area"]):
                    self.set_aggregation_area(config["aggregation_area"])
            elif self.selection_type == "polygon" and validate_content_config_file(config, self.config_file, ["polygon_file"]):
                self.set_polygon_file(config["polygon_file"])

            self.set_property_type(config["property_type"])
            
        return self
