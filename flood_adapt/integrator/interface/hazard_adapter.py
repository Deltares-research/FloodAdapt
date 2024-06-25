from abc import abstractmethod

from flood_adapt.integrator.interface.model_adapter import IAdapter, ModelData
from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.hazard.event.new_event_models import EventModel
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection


class HazardData(ModelData):
    pass


class IHazardAdapter(IAdapter):
    @abstractmethod
    def set_timing(self, event: EventModel):
        """
        Implement this to handle the timing of the event from the EventModel.

        Access the events timing by `event.timing`, which contains the start and end time of the event, and the time step.
        """
        pass

    @abstractmethod
    def add_forcing(self, forcing: IForcing):
        """
        Implement this to handle each supported forcing type for this Hazard model.

        A forcing is time series data, i.e. water levels, wind, rain, discharge, with optional time and space dimensions.
        So this could be a single time series, or a collection of time series, or a time series associated with a spatial grid/gridpoint)

        Forcings contain all information needed to implement the forcing in the hazard model. (geospatial files, parameters, etc.)
        """
        pass

    @abstractmethod
    def add_measure(self, measure: HazardMeasure):
        """
        Implement this to handle each supported measure type for this Hazard model.

        A hazardmeasure is a measure that affects the hazard model, i.e. a measure that affects the water levels, wind, rain, discharge.
        For example a measure could be a dike, a land use change, a change in the river channel, etc.

        HazardMeasures contain all information needed to implement the measure in the hazard model. (geospatial files, parameters, etc.)

        """
        pass

    @abstractmethod
    def add_projection(self, projection: PhysicalProjection):
        """
        Implement this to handle each supported projection type for this Hazard model.

        A projection is a projection of the future, i.e. sea level rise, subsidence, rainfall multiplier, storm frequency increase, etc.
        PhysicalProjections contains all information needed to implement the projection in the hazard model. (parameters, etc.)
        """
        pass
