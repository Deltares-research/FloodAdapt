from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
    ImpactMeasureModel,
)
from flood_adapt.object_model.interface.measures import IElevate


class ElevateModel(ImpactMeasureModel):
    pass


class Elevate(ImpactMeasure, IElevate):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height"""

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
        if validate_content_config_file(
            self._config, self.config_file, self.mandatory_keys
        ):
            self.elevation = self._config["elevation"]

        return self
