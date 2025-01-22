from abc import abstractmethod

from flood_adapt.adapter.interface.model_adapter import IAdapter
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.interface.projections import IProjection


class IImpactAdapter(IAdapter):
    @abstractmethod
    def add_measure(self, measure: IMeasure):
        """
        Implement this to handle each supported measure type for this Impact model.

        An impact measure is a measure that affects the impact model, i.e. a measure that affects the elevation of buildings.
        For example a measure could be buyouts, floodproofing etc.

        ImpactMeasures contain all information needed to implement the measure in the impact model. (geospatial files, parameters, etc.)

        """
        pass

    @abstractmethod
    def add_projection(self, projection: IProjection):
        """
        Implement this to handle each supported projection type for this Impact model.

        A projection is a projection of the future, i.e. economic growth, etc.
        SocioEconomicChange contains all information needed to implement the projection in the impact model. (parameters, etc.)
        """
        pass

    @abstractmethod
    def set_hazard(self, floodmap: FloodMap):
        """Implement this to handle setting up of a hazard flood map."""
        pass
