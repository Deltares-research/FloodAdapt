import tomli
from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.io.unitfulvalue import UnitfulValue


class TimeModel(BaseModel):
    duration_before_t0: float
    duration_after_t0: float


class TideModel(BaseModel):
    source: str
    harmonic_amplitude: UnitfulValue


class SyntheticModel(BaseModel):  # add SurgeModel etc. that fit Synthetic event
    time: TimeModel
    tide: TideModel


class Synthetic(Event):
    synthetic: SyntheticModel

    def __init__(self) -> None:
        self.set_default()

    def set_default(self):
        super().set_default()
        self.synthetic = SyntheticModel(
            time=TimeModel(duration_before_t0=24.0, duration_after_t0=24.0),
            tide=TideModel(
                source="harmonic",
                harmonic_amplitude=UnitfulValue(value=1.0, units="meters"),
            ),
        )

    def load(self, filepath: str):
        super().load(filepath)

        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        self.synthetic = SyntheticModel.parse_obj(toml)
        return self
