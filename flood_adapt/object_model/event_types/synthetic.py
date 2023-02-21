from object_model.event import Event

class Synthetic(Event):
    def __init__(self, config_file: str = None) -> None:
        super().__init__(config_file = config_file)
        self.set_default()

    def set_default(self):
        self.timing = 'Idealized'
        self.time_before_T0 = 0.
        self.time_after_T0 = 0.
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

    def set_tide(self, values: dict) -> None:
        self.tide_source = values.tide_source
        self.tide_amplitude = values.tide_amplitude

    def set_surge(self, values: dict) -> None:
        self.surge_source = values.surge_source
        if self.surge_source == 'shape':
            self.surge_peak = values.surge_peak
            self.surge_peak_time = values.surge_peak_time
            self.surge_duration = values.surge_duration

    def set_wind(self, values: dict) -> None:
        self.wind_source = values.wind_source
        if self.wind_source == 'constant':
            self.wind_speed = values.wind_speed
            self.wind_dir = values.wind_dir

    def set_rainfall(self, values: dict) -> None:
        self.rainfall_source = values.rainfall_source
        if self.rainfall_source == 'constant':
            self.rainfall_intensity = values.rainfall_intensity
        if self.rainfall_source == 'shape':
            self.rainfall_shape = values.rainfall_shape
            if self.rainfall_shape == 'gaussian':
                self.rainfall_cumulative = values.rainfall_cumulative
                self.rainfall_peak_time = values.rainfall_peak_time
                self.rainfall_duration = values.rainfall_duration

    def set_river(self, values: dict) -> None: # // TODO Deal with Multiple rivers or no rivers
        self.river_source = values.river_source
        self.river_name = None
        if self.river_source == 'constant':
            self.river_discharge = values.river_discharge
        if self.river_source == 'shape':
            self.river_source_shape = values.river_source_shape
            if self.river_source_shape == 'gaussian':
                self.river_base_discharge = values.river_base_discharge
                self.river_peak_discharge = values.river_peak_discharge
                self.river_discharge_duration = values.river_discharge_duration
    
    def load(self):
        if self.validate_existence_config_file():
            config = read_config(self.inputfile)

        if self.validate_content_config_file(config):
            self.set_name(config["name"])
            self.set_name(config["long_name"])
            self.set_tide(config["tide"])
            self.set_surge(config["surge"])
            self.set_wind(config["wind"])
            self.set_rainfall(config["rainfall"])
            self.set_river(config["river"])
      
    
    # def write(self):
    #     write_config(self.config_file)
