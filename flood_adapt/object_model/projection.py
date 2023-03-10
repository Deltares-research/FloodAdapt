from pathlib import Path

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
    SocioEconomicChangeModel,
)
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
    PhysicalProjectionModel,
)
from flood_adapt.object_model.interface.projections import IProjection


class ProjectionModel(PhysicalProjectionModel, SocioEconomicChangeModel):
    name: str
    long_name: str


class Projection(IProjection):
    """Projection class that holds all the information for a specific projection"""

    attrs: ProjectionModel

    def get_physical_projection(self) -> PhysicalProjection:
        return PhysicalProjection(self.attrs.dict(exclude_none=True))

    def get_socio_economic_change(self) -> SocioEconomicChange:
        return SocioEconomicChange(self.attrs.dict(exclude_none=True))

    @staticmethod
    def load_file(filepath: Path):
        """create Projection from toml file"""

        obj = Projection()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ProjectionModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Projection from object, e.g. when initialized from GUI"""

        obj = Projection()
        obj.attrs = ProjectionModel.parse_obj(data)
        return obj

    def save(self, filepath: Path):
        """save Elavate to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
