import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.physical_projection import PhysicalProjection
from flood_adapt.object_model.interface.projections import IProjection, ProjectionModel
from flood_adapt.object_model.utils import import_external_file


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
        """Save ProjectionModel to a toml file, save any external files and update the paths in the object."""
        if self.attrs.socio_economic_change.new_development_shapefile:
            new_path = import_external_file(
                self.attrs.socio_economic_change.new_development_shapefile,
                Path(filepath).parent,
            )
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.socio_economic_change.new_development_shapefile = str(new_path)

        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
