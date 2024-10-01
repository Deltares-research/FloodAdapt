from abc import abstractmethod

from flood_adapt.integrator.interface.model_adapter import IAdapter
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
)


class IImpactAdapter(IAdapter):
    @abstractmethod
    def add_measure(self, measure: ImpactMeasure):
        """
        Implement this to handle each supported measure type for this Hazard model.

        A impactmeasure is a measure that affects the impact model, i.e. a measure that affects the water levels, wind, rain, discharge.
        For example a measure could be a dike, a land use change, a change in the river channel, etc.

        ImpactMeasures contain all information needed to implement the measure in the impact model. (geospatial files, parameters, etc.)

        """
        pass

    @abstractmethod
    def add_projection(self, projection: PhysicalProjection):
        """
        Implement this to handle each supported projection type for this Hazard model.

        A projection is a projection of the future, i.e. sea level rise, subsidence, rainfall multiplier, storm frequency increase, etc.
        PhysicalProjections contains all information needed to implement the projection in the impact model. (parameters, etc.)
        """
        pass
