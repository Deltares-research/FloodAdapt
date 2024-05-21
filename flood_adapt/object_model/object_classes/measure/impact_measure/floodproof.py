from flood_adapt.object_model.models.measures import FloodProofModel
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)


class FloodProof(ImpactMeasure):
    """Subclass of ImpactMeasure describing the measure of flood-proof buildings"""

    _attrs = FloodProofModel