import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.hazard.measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.interface.measures import (
    IPump,
    PumpModel,
)


class Pump(HazardMeasure, IPump):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height"""

    attrs: PumpModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IPump:
        """create Floodwall from toml file"""

        obj = Pump()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = PumpModel.parse_obj(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike]
    ) -> IPump:
        """create Floodwall from object, e.g. when initialized from GUI"""

        obj = Pump()
        obj.attrs = PumpModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Floodwall to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
