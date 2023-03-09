from pathlib import Path

import tomli
import tomli_w

from flood_adapt.object_model.hazard.measure.hazard_measure import (
    HazardMeasure,
    HazardMeasureModel,
)
from flood_adapt.object_model.interface.measures import IFloodwall
from flood_adapt.object_model.io.unitfulvalue import UnitfulLengthRefValue


class FloodwallModel(HazardMeasureModel):
    elevation: UnitfulLengthRefValue


class FloodWall(HazardMeasure, IFloodwall):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height"""

    attrs: FloodwallModel

    @staticmethod
    def load_file(filepath: Path):
        """create Floodwall from toml file"""

        obj = FloodWall()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = FloodwallModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Floodwall from object, e.g. when initialized from GUI"""

        obj = FloodWall()
        obj.attrs = FloodwallModel.parse_obj(data)
        return obj

    def save(self, filepath: Path):
        """save Floodwall to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
