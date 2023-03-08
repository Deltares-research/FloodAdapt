from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.interface.measures import IElevate, Elevation
from flood_adapt.object_model.validate.config import (
    validate_content_config_file,
    validate_existence_config_file,
)


class Elevate(ImpactMeasure, IElevate):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height"""

    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        """Sets the default values of the Elevate class attributes"""
        super().set_default()
        self.type = "elevate_properties"  # name reference that is used to know which class to use when the config file is read
        elevation = dict()
        elevation["value"] = 0  # the height to elevate the properties by
        elevation["units"] = "m"  # the units that the height is given
        elevation["type"] = "datum"  # type of height reference (can be "floodmap" or "datum")
        self.elevation = elevation
        self.mandatory_keys.extend(["elevation"])

    @property
    def elevation(self):
        return self._elevation

    @elevation.setter
    def elevation(self, value: Elevation):
        self._elevation = Elevation(**value)

    def load(self, config_file: str = None):
        """loads and updates the class attributes from a configuration file"""
        super().load(config_file)
        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(self._config, self.config_file, self.mandatory_keys):
            self.elevation = self._config["elevation"]

        return self
