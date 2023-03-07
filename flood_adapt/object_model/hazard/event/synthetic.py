from pathlib import Path
import tomli
from pydantic import BaseModel, ValidationError

from flood_adapt.object_model.hazard.event.event import Event
# from flood_adapt.object_model.io.config_io import read_config, write_config
# from flood_adapt.object_model.validate.config import validate_content_config_file
from flood_adapt.object_model.io.unitfulvalue import UnitfulValue

class TideModel(BaseModel):
    source: str
    harmonic_amplitude : UnitfulValue

class SyntheticModel(BaseModel):
    duration_before_t0 : float
    duration_after_t0 : float
    tide: TideModel

class Synthetic(Event):
    duration_before_t0 : float
    duration_after_t0 : float
    tide: TideModel

    def __init__(self) -> None:
        super().__init__()
        self.set_default()

    def set_default(self):
        super().set_default()
        self.duration_before_t0 = 24.
        self.duration_after_t0 = 24.
        self.tide = TideModel(source='harmonic', harmonic_amplitude=UnitfulValue(value=1, units="m"))
        # self.mandatory_keys.extend(["duration_before_t0", "duration_after_t0"])

    def set_name(self, value: str) -> None:
        self.name = value

    def set_long_name(self, value: str) -> None:
        self.long_name = value

    def set_duration_before_t0(self, value: float) -> None:
        self.duration_before_t0 = value

    def set_duration_after_t0(self, value: float) -> None:
        self.duration_after_t0 = value

    def set_tide(self, tide: TideModel) -> None:
        self.tide = tide

    # def set_surge(self, surge: dict) -> None:
    #     self.surge["source"] = surge["source"]
    #     self.surge["panel_text"] = surge["panel_text"]
    #     if self.surge["source"] == "shape":
    #         self.surge["shape_type"] = surge["shape_type"]
    #         if self.surge["shape_type"] == "gaussian":
    #             self.surge["shape_peak"] = surge["shape_peak"]
    #             self.surge["shape_duration"] = surge["shape_duration"]
    #             self.surge["shape_peak_time"] = surge["shape_peak_time"]

    # def set_wind(self, wind: dict) -> None:
    #     self.wind["source"] = wind["source"]
    #     if self.wind["source"] == "constant":
    #         self.wind["constant_speed"] = wind["constant_speed"]
    #         self.wind["constant_direction"] = wind["constant_direction"]

    # def set_rainfall(self, rainfall: dict) -> None:
    #     self.rainfall["source"] = rainfall["source"]
    #     if self.rainfall["source"] == "constant":
    #         self.rainfall["intensity"] = rainfall["intensity"]
    #     if self.rainfall["source"] == "shape":
    #         self.rainfall["shape_type"] = rainfall["shape_type"]
    #         if self.rainfall["shape_type"] == "gaussian":
    #             self.rainfall["cumulative"] = rainfall["cumulative"]
    #             self.rainfall["peak_time"] = rainfall["peak_time"]
    #             self.rainfall["duration"] = rainfall["duration"]

    # def set_river(
    #     self, river: dict
    # ) -> None:  # // TODO Deal with Multiple rivers or no rivers
    #     self.river["source"] = river["source"]
    #     if self.river["source"] == "constant":
    #         self.river["constant_discharge"] = river["constant_discharge"]
    #     if self.river["source"] == "shape":
    #         self.river["shape_type"] = river["shape_type"]
    #         if self.river["shape_type"] == "gaussian":
    #             self.river["base_discharge"] = river["base_discharge"]
    #             self.river["peak_discharge"] = river["peak_discharge"]
    #             self.river["discharge_duration"] = river["discharge_duration"]

    def load(self, filepath: str):
        super().load(filepath)

        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        try:
            synthetic = SyntheticModel.parse_obj(toml)
        except ValidationError as e:
            print(e)

        # if validate_content_config_file(config, config_file, self.mandatory_keys):
        self.set_duration_before_t0(synthetic.duration_before_t0)
        self.set_duration_after_t0(synthetic.duration_after_t0)
        self.set_tide(synthetic.tide)
            # self.set_surge(config["surge"])
            # self.set_wind(config["wind"])
            # self.set_rainfall(config["rainfall"])
            # self.set_river(config["river"])
        return self

    def write(self):
        ...

    #     write_config(self.config_file)
