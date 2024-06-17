from abc import ABC, abstractmethod

from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.events import IForcing


class IHazardAdapter(ABC):
    @abstractmethod
    def __enter__(self):
        """Use the adapter as a context manager to handle opening/closing of the hazard model and attached resources.

        This method should return the adapter object itself, so that it can be used in a with statement.

        Usage:

        with Adapter as model:
            ...
            model.run()

        Entering the with block will call adapter.__enter__() and
        Exiting the with block (via regular execution or an error) will call adapter.__exit__()
        """
        pass

    @abstractmethod
    def __exit__(self):
        """Use the adapter as a context manager to handle opening/closing of the hazard model and attached resources.

        This method should return the adapter object itself, so that it can be used in a with statement.

        Usage:

        with Adapter as model:
            ...
            model.run()

        Entering the `with` block will call adapter.__enter__()
        Exiting the `with` block (via regular execution or an error) will call adapter.__exit__()
        """
        pass

    @abstractmethod
    def read(self):
        pass

    @abstractmethod
    def write(self):
        pass

    @abstractmethod
    def run(self):
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
