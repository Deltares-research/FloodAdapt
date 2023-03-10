from pathlib import Path
from typing import Union

import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.io.database_io import DatabaseIO
from flood_adapt.object_model.site import SiteConfig


class ScenarioModel(BaseModel):
    """BaseModel describing the expected variables and data types of the scenario"""

    name: str
    long_name: str
    event: str
    projection: str
    strategy: str


class Scenario:  # TODO: add IScenario
    """The Scenario class containing all information on a single scenario."""

    attrs: ScenarioModel

    def init(self):
        self.site_info = SiteConfig(DatabaseIO().site_config_path)
        self.direct_impacts = DirectImpacts(self.attrs)

    @staticmethod
    def load_file(filepath: Union[Path, str]):
        """create Scenario from toml file"""

        obj = Scenario()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ScenarioModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Scenario from object, e.g. when initialized from GUI"""

        obj = Scenario()
        obj.attrs = ScenarioModel.parse_obj(data)
        return obj

    def save(self, filepath: Path):
        """save Elavate to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
