from flood_adapt.object_model.io.config_io import read_config
from flood_adapt.object_model.validate.config import validate_existence_config_file, validate_content_config_file
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure

class FloodWall(HazardMeasure):
    """ Subclass of Measure describing the measure of elevating buildings by a specific height
    """
    def __init__(self, config_file: str = None) -> None:
        super().__init__(config_file)

    def set_default(self):
        """ Sets the default values of the floodwall class attributes
        """
        super().set_default()
        self.type = "floodwall"  # name reference that is used to know which class to use when the config file is read
        self.elevation = {}
        self.elevation["value"] = None # elevation of flood wall
        self.elevation["units"] = "m"  # the units that the height is given
        self.elevation["type"] = "floodmap"  # type of height reference (can be "floodmap" or "datum")
        self.polygon_file = None  # polygon file to use 
        self.datum = None  # what is this for?
        self.mandatory_keys.extend(["type","elevation", "polygon_file"])

    def set_type(self, type: str):
        self.type = type

    def set_elevation(self, elevation, elevation_vert_units, elevation_type):
        self.elevation["value"] = elevation
        self.elevation["units"] = elevation_vert_units
        self.elevation["type"] = elevation_type

    def set_polygon_file(self, polygon_file):
        self.polygon_file = polygon_file

    def set_datum(self, datum):
        self.datum = datum

    def load(self):
        """ loads and updates the class attributes from a configuration file
        """
        super().load()
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            config = read_config(self.config_file)
            config_keys = config.keys()

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(config, self.config_file, self.mandatory_keys):
            self.set_type(config["type"])
            self.set_elevation(config["elevation"], config["elevation_vertical_units"], config["elevation_type"])
            if "datum" in config_keys:
                self.set_datum(config["datum"])
        return self
