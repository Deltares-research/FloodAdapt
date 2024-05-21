from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.models.measures import MeasureModel
from flood_adapt.object_model.object_classes.flood_adapt_object import (
    FAObject,
)


class Measure(IMeasure, FAObject):
    """Measure class that holds all the information for a specific measure type"""

    _attrs = MeasureModel
    _type = "Measures"

    def get_measure_type(self) -> str:
        """Returns the type of the measure

        Returns
        -------
        str
            The type of the measure
        """

        return self._attrs.type
