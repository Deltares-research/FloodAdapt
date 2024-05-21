from abc import ABC, abstractmethod

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection


class IProjection(ABC):
    @abstractmethod
    def get_physical_projection(self) -> PhysicalProjection:
        """Get the physical projection of the object

        Returns
        -------
        PhysicalProjection
            The physical projection of the object
        """
        ...

    @abstractmethod
    def get_socio_economic_change(self) -> SocioEconomicChange:
        """Get the socio-economic change of the object

        Returns
        -------
        SocioEconomicChange
            The socio-economic change of the object
        """
        ...
