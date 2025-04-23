from abc import abstractmethod
from typing import Any

import geopandas as gpd

from flood_adapt.adapter.interface.model_adapter import IAdapter
from flood_adapt.objects.forcing.forcing import IForcing
from flood_adapt.objects.forcing.time_frame import TimeFrame
from flood_adapt.objects.measures.measures import Measure
from flood_adapt.objects.projections.projections import Projection


class IHazardAdapter(IAdapter):
    @abstractmethod
    def set_timing(self, time: TimeFrame):
        """
        Implement this to handle the timing of the event from the Event.

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
    def add_measure(self, measure: Measure):
        """
        Implement this to handle each supported measure type for this Hazard model.

        A hazardmeasure is a measure that affects the hazard model, i.e. a measure that affects the water levels, wind, rain, discharge.
        For example a measure could be a dike, a land use change, a change in the river channel, etc.

        HazardMeasures contain all information needed to implement the measure in the hazard model. (geospatial files, parameters, etc.)

        """
        pass

    @abstractmethod
    def add_projection(self, projection: Projection):
        """
        Implement this to handle each supported projection type for this Hazard model.

        A projection is a projection of the future, i.e. sea level rise, subsidence, rainfall multiplier, storm frequency increase, etc.
        PhysicalProjections contains all information needed to implement the projection in the hazard model. (parameters, etc.)
        """
        pass

    @abstractmethod
    def get_model_boundary(self) -> gpd.GeoDataFrame:
        """
        Implement this to return the model boundary of the hazard model.

        The model boundary is a geospatial file that defines the boundary of the hazard model.
        """
        pass

    @abstractmethod
    def get_model_grid(self) -> Any:
        """Implement this to return the model grid of the hazard model."""
        pass
