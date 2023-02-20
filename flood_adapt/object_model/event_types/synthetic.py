from object_model.event import Event

class Synthetic(Event):
    def __init__(self):
        self.timing = 'Idealized'
        self.time_before_T0 = 0.
        self.time_after_T0 = 0.
        self.tide = 'harmonic'
        self.tide_amplitude = 0.
        self.surge_source = None
        if self.surge_source == 'shape':
            self.surge_peak = 0.
            self.surge_peak_time = 0.
            self.surge_duration = 0.
        self.wind_source = None
        if self.wind_source == 'constant':
            self.wind_speed = 0.
            self.wind_dir = 0.
        self.rainfall_source = None
        if self.rainfall_source == 'constant':
            self.rainfall_intensity = 0.
        if self.rainfall_source == 'shape':
            if self.rainfall_type == 'gaussian':
                self.rainfall_cumulative = 0.
                self.rainfall_peak_time = 0.
                self.rainfall_duration = 0.
        self.river_source = None
        if self.river_source == 'constant':
            self.river_name = None
            self.river_discharge = 0.
        if self.river_source == 'shape':
            if self.river_type == 'gaussian':
                self.river_name = None
                self.river_base_discharge = 0.
                self.river_peak_discharge = 0.
                self.river_peak_discharge_time = 0.
                self.river_discharge_duration = 0.
            
