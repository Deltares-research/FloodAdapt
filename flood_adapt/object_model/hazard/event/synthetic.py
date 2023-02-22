from pathlib import Path

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.io.config_io import read_config, write_config

class Synthetic(Event):
    def __init__(self, config_file: str = None) -> None:
        super().__init__(config_file = config_file)
        self.set_default()
        if config_file:
            self.config_file = config_file

    def set_default(self):
        super().set_default()
        self.duration_before_t0 = 0
        self.duration_after_t0 = 0
        self.mandatory_keys = ["template", "timing","duration_before_t0","duration_after_t0"]

    def validate_existence_config_file(self):
        if self.config_file:
            if Path(self.config_file).is_file():
                return True
            else:
                raise FileNotFoundError("Cannot find synthetic event configuration file {}.".format(self.config_file))

    def validate_content_config_file(self, config):
        not_found_in_config = []
        for mandatory_key in self.mandatory_keys:
            if mandatory_key not in config.keys():
                not_found_in_config.append(mandatory_key)
        
        if not_found_in_config:
            raise ValueError("Cannot find mandatory key(s) '{}' in configuration file {}.".format(', '.join(not_found_in_config), self.config_file))
        else:
            return True

    def set_name(self, value: str) -> None:
        self.name = value
    
    def set_long_name(self, value: str) -> None:
        self.long_name = value

    def set_template(self, value: str) -> None:
        self.template = value

    def set_timing(self, value: str) -> None:
        self.timing = value

    def set_duration_before_t0(self, value: str) -> None:
        self.duration_before_t0 = value

    def set_duration_after_t0(self, value: str) -> None:
        self.duration_after_t0 = value

    def set_water_level_offset(self, value: dict) -> None:
        self.water_level_offset = {'value': value["value"], 'units': value["units"]}

    def set_tide(self, tide: dict) -> None:
        self.tide = {"source": tide["source"]}
        self.tide["harmonic_amplitude"] = {"value": tide["harmonic_amplitude"]["value"], "units": tide["harmonic_amplitude"]["units"]}

    def set_surge(self, surge: dict) -> None:
        self.surge = {'source': surge["source"], 'panel_text': surge["panel_text"]}
        if self.surge['source'] == 'shape':
            self.surge['shape'] = surge["shape"]
            if self.surge.shape == 'gaussian':
                self.surge.shape_peak.value = surge.shape_peak.value
                self.surge.shape_peak.units = surge.shape_peak.units
                self.surge.shape_duration = surge.shape_duration
                self.surge.shape_peak_time = surge.surge.shape_peak_time

    def set_wind(self, wind: dict) -> None:
        self.wind.source = wind.source
        if self.wind.source == 'constant':
            self.wind.constant_speed.value = wind.constant_speed.value
            self.wind.constant_speed.units = wind.constant_speed.units
            self.wind.constant_direction.value = wind.constant_direction.value
            self.wind.constant_direction.units = wind.constant_direction.units

    def set_rainfall(self, rainfall: dict) -> None:
        self.rainfall.source = rainfall.rainfall_source
        if self.rainfall.source == 'constant':
            self.rainfall.intensity.value = rainfall.intensity.value
            self.rainfall.intensity.units = rainfall.intensity.units
        if self.rainfall.source == 'shape':
            self.rainfall.shape = rainfall.rainfall.shape
            if self.rainfall.shape == 'gaussian':
                self.rainfall.cumulative.value = rainfall.cumulative.value
                self.rainfall.cumulative.units = rainfall.cumulative.units
                self.rainfall.peak_time = rainfall.peak_time
                self.rainfall.duration = rainfall.duration

    def set_river(self, river: dict) -> None: # // TODO Deal with Multiple rivers or no rivers
        self.river.source = river.source
        if self.river.source == 'constant':
            self.river.constant_discharge.value = river.constant_discharge.value
            self.river.constant_discharge.units = river.constant_discharge.units
        if self.river_source == 'shape':
            self.river.source_shape = river.source_shape
            if self.river_source_shape == 'gaussian':
                self.river.base_discharge.value = river.base_discharge.value
                self.river.base_discharge.units = river.base_discharge.units
                self.river.peak_discharge.value = river.peak_discharge.value
                self.river.peak_discharge.units = river.peak_discharge.units
                self.river.discharge_duration = river.discharge_duration
    
    def load(self):
        if self.validate_existence_config_file():
            config = read_config(self.config_file)

        if self.validate_content_config_file(config):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
            self.set_template(config["template"])
            self.set_timing(config["timing"])
            self.set_duration_before_t0(config["duration_before_t0"])
            self.set_duration_after_t0(config["duration_after_t0"])
            self.set_water_level_offset(config["water_level_offset"])
            self.set_tide(config["tide"])
            self.set_surge(config["surge"])
            self.set_wind(config["wind"])
            self.set_rainfall(config["rainfall"])
            self.set_river(config["river"])
      
    
    # def write(self):
    #     write_config(self.config_file)
