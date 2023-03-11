import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
    ImpactMeasureModel,
)
from flood_adapt.object_model.interface.measures import IMeasure
from flood_adapt.object_model.io.unitfulvalue import UnitfulLengthRefValue


class ElevateModel(ImpactMeasureModel):
    elevation: UnitfulLengthRefValue


class Elevate(ImpactMeasure, IMeasure):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height"""

    attrs: ElevateModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Elevate from toml file"""

        obj = Elevate()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ElevateModel.parse_obj(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """create Elevate from object, e.g. when initialized from GUI"""

        obj = Elevate()
        obj.attrs = ElevateModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Elevate to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
