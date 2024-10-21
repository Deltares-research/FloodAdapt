import os
from typing import Union

import tomli

from flood_adapt.object_model.interface.measures import (
    HazardType,
    ImpactType,
    MeasureModel,
)


# I think this is not used anywhere, TODO check & remove this class if its not used
class Measure:
    attrs: MeasureModel

    @staticmethod
    def get_measure_type(filepath: Union[str, os.PathLike]):
        """Get a measure type from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        type = toml.get("type")
        if type in ImpactType.__members__.values():
            return ImpactType(type)
        elif type in HazardType.__members__.values():
            return HazardType(type)
        else:
            raise ValueError(f"Invalid measure type: {type}")
