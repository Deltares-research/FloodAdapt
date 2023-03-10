import os
from typing import Any, Union

import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
    SocioEconomicChangeModel,
)
from flood_adapt.object_model.hazard.physical_projection import (
    PhysicalProjection,
    PhysicalProjectionModel,
)
from flood_adapt.object_model.interface.projections import IProjection


class ProjectionModel(BaseModel):
    name: str
    long_name: str
    physical_projection: PhysicalProjectionModel
    socio_economic_change: SocioEconomicChangeModel


class Projection(IProjection):
    """Projection class that holds all the information for a specific projection"""

    attrs: ProjectionModel

    def get_physical_projection(self) -> PhysicalProjection:
        return PhysicalProjection(self.attrs.physical_projection)

    def get_socio_economic_change(self) -> SocioEconomicChange:
        return SocioEconomicChange(self.attrs.socio_economic_change)

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Projection from toml file"""

        obj = Projection()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ProjectionModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Projection from object, e.g. when initialized from GUI"""

        obj = Projection()
        obj.attrs = ProjectionModel.parse_obj(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Elavate to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
