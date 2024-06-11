import os
from typing import Union

import tomli

from flood_adapt.object_model.interface.measures import MeasureModel


class Measure:
    attrs: MeasureModel

    @staticmethod
    def get_measure_type(filepath: Union[str, os.PathLike]):
        """Get a measure type from toml file."""
        obj = Measure()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = MeasureModel.model_validate(toml)
        return obj.attrs.type
