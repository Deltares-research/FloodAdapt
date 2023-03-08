from pathlib import Path

import tomli
import tomli_w
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event, EventModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength


class TimeModel(BaseModel):
    """BaseModel describing the expected variables and data types for time parameters of synthetic model"""

    duration_before_t0: float
    duration_after_t0: float


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model"""

    source: str
    harmonic_amplitude: UnitfulLength


class SyntheticModel(EventModel):  # add SurgeModel etc. that fit Synthetic event
    """BaseModel describing the expected variables and data types for parameters of Synthetic that extend the parent class Event"""

    time: TimeModel
    tide: TideModel


class Synthetic(Event):
    """class for Synthetic event, can only be initialized from a toml file or dictionar using load_file or load_dict"""

    model: SyntheticModel

    @staticmethod
    def load_file(filepath: Path):
        """create Synthetic from toml file"""

        obj = Synthetic()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.model = SyntheticModel.parse_obj(toml)
        return obj

    @staticmethod
    def load_dict(data: dict):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = Synthetic()
        obj.model = SyntheticModel.parse_obj(data)
        for key, value in obj.model.dict().items():
            setattr(obj, key, value)
        return obj

    def save(self, file: Path):
        with open(file, "wb") as f:
            tomli_w.dump(self.model.dict(), f)
