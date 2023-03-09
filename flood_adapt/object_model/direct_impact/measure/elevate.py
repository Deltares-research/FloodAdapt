import tomli
import tomli_w
from click import Path

from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
    ImpactMeasureModel,
)
from flood_adapt.object_model.interface.measures import IElevate
from flood_adapt.object_model.io.unitfulvalue import UnitfulLengthRefValue


class ElevateModel(ImpactMeasureModel):
    elevation: UnitfulLengthRefValue


class Elevate(ImpactMeasure, IElevate):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height"""

    attrs: ElevateModel

    @staticmethod
    def load_file(filepath: Path):
        """create Elevate from toml file"""

        obj = Elevate()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ElevateModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Elevate from object, e.g. when initialized from GUI"""

        obj = Elevate()
        obj.attrs = ElevateModel.parse_obj(data)
        return obj

    def save(self, filepath: Path):
        """save Elevate to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
