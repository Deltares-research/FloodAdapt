from flood_adapt.object_model.models.measures import BuyoutModel
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)


class Buyout(ImpactMeasure):
    """Subclass of ImpactMeasure describing the measure of buying-out buildings"""

    _attrs = BuyoutModel

