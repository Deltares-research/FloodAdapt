import os
from typing import Union

import tomli
from pydantic import BaseModel


class MeasureModel(BaseModel):
    """"""

    name: str
    long_name: str
    type: str


class Measure:
    attrs: MeasureModel

    @staticmethod
    def get_measure_type(filepath: Union[str, os.PathLike]):
        """get a measure type from toml file"""

        obj = Measure()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = MeasureModel.parse_obj(toml)
        return obj.attrs.type
