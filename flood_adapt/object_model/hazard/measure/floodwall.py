import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.hazard.measure.hazard_measure import (
    HazardMeasure,
    HazardMeasureModel,
)
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.io.unitfulvalue import UnitfulLengthRefValue


class FloodwallModel(HazardMeasureModel):
    elevation: UnitfulLengthRefValue


class FloodWall(HazardMeasure, IMeasure):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height"""

    attrs: FloodwallModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Floodwall from toml file"""

        obj = FloodWall()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = FloodwallModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Floodwall from object, e.g. when initialized from GUI"""

        obj = FloodWall()
        obj.attrs = FloodwallModel.parse_obj(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Floodwall to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
