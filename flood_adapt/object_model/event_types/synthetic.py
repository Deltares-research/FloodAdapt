from pathlib import Path

from object_model.event import Event
from flood_adapt.object_model.io.config_io import read_config, write_config

class Synthetic(Event):
    def __init__(self, config_file: str = None) -> None:
        super().__init__(config_file = config_file)
        self.set_default()

    def set_default(self):
        self.timing = 'Idealized'
        self.time_before_T0 = 0.
        self.time_after_T0 = 0.
        self.water_level_offset.value = 0.
        self.water_level_offset.units = "meter"
        self.mandatory_keys = ["name", "long_name"]

    def validate_existence_config_file(self):
        if self.config_file:
            if Path(self.config_file).is_file():
                return True
        
        raise FileNotFoundError("Cannot find projection configuration file {}.".format(self.config_file))

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

    def set_water_level_offset(self, value: dict) -> None:
        self.water_level_offset.value = value.value
        self.water_level_offset.units = value.units

    def set_tide(self, tide: dict) -> None:
        self.tide.source = tide.source
        self.tide.harmonic_amplitude.value = tide.harmonic_amplitude.value
        self.tide.harmonic_amplitude.units = tide.harmonic_amplitude.units

    def set_surge(self, surge: dict) -> None:
        self.surge.source = surge.source
        self.surge.panel_text = surge.panel_text
        if self.surge.source == 'shape':
            self.surge.shape_type = surge.shape_type
            if self.surge.shape_type == 'gaussian':
                self.surge.shape_peak.value = surge.shape_peak.value
                self.surge.shape_peak.units = surge.shape_peak.units
                self.surge.shape_duration = surge.shape_duration
                self.surge.shape_peak_time = surge.surge.shape_peak_time

    def set_wind(self, wind: dict) -> None:
        self.wind.source = wind.source
        if self.wind_source == 'constant':
            self.wind.constant_speed.value = wind.constant_speed.value
            self.wind.constant_speed.units = wind.constant_speed.units
            self.wind.constant_direction.value = wind.constant_direction.value
            self.wind.constant_direction.units = wind.constant_direction.units

    def set_rainfall(self, rainfall: dict) -> None:
        self.rainfall_source = rainfall.rainfall_source
        if self.rainfall_source == 'constant':
            self.rainfall_intensity.value = rainfall.rainfall_intensity.value
            self.rainfall_intensity.units = rainfall.rainfall_intensity.units
        if self.rainfall_source == 'shape':
            self.rainfall_shape = rainfall.rainfall_shape
            if self.rainfall_shape == 'gaussian':
                self.rainfall_cumulative.value = rainfall.rainfall_cumulative.value
                self.rainfall_cumulative.units = rainfall.rainfall_cumulative.units
                self.rainfall_peak_time = rainfall.rainfall_peak_time
                self.rainfall_duration = rainfall.rainfall_duration

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
            config = read_config(self.inputfile)

        if self.validate_content_config_file(config):
            self.set_name(config["name"])
            self.set_name(config["long_name"])
            self.set_water_level_offset(config["water_level_offset"])
            self.set_tide(config["tide"])
            self.set_surge(config["surge"])
            self.set_wind(config["wind"])
            self.set_rainfall(config["rainfall"])
            self.set_river(config["river"])
      
    
    # def write(self):
    #     write_config(self.config_file)
