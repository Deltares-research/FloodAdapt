import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.projections import IProjection, ProjectionModel


class Projection(IProjection):
    """Projection class that holds all the information for a specific projection."""

    attrs: ProjectionModel

    def get_physical_projection(self) -> PhysicalProjection:
        return PhysicalProjection(self.attrs.physical_projection)

    def get_socio_economic_change(self) -> SocioEconomicChange:
        return SocioEconomicChange(self.attrs.socio_economic_change)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Create Projection from toml file."""
        obj = Projection()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ProjectionModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """Create Projection from object, e.g. when initialized from GUI."""
        obj = Projection()
        obj.attrs = ProjectionModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Projection to a toml file."""
        if not os.path.exists(filepath):
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
