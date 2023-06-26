import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.interface.benefits import BenefitModel, IBenefit


class Benefit(IBenefit):
    """class holding all information related to a benefit analysis"""

    attrs: BenefitModel
    database_input_path: Union[str, os.PathLike]

    def check_scenarios(self):
        ...

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Benefit from toml file"""

        obj = Benefit()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = BenefitModel.parse_obj(toml)
        # if benefits is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """create Benefit from object, e.g. when initialized from GUI"""

        obj = Benefit()
        obj.attrs = BenefitModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Benefit to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
