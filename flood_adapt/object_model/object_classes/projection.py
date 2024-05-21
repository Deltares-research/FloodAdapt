from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.models.projections import ProjectionModel
from flood_adapt.object_model.object_classes.flood_adapt_object import FAObject


class Projection(FAObject, IProjection):
    """This class represents a Projection object, holding all information about a projection"""

    _attrs = ProjectionModel
    _type: str = "Projection"

    def get_physical_projection(self) -> PhysicalProjection:
        """Get the physical projection of the object

        Returns
        -------
        PhysicalProjection
            The physical projection of the object
        """
        return PhysicalProjection(self.attrs.physical_projection)

    def get_socio_economic_change(self) -> SocioEconomicChange:
        """Get the socio-economic change of the object

        Returns
        -------
        SocioEconomicChange
            The socio-economic change of the object
        """
        return SocioEconomicChange(self.attrs.socio_economic_change)