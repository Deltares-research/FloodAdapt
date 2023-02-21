from flood_adapt.object_model.risk_drivers.risk_driver import RiskDriver


class GrowthNew(RiskDriver):
    def __init__(self) -> None:
        super().__init__()
        self.set_default()

        # sea_level_rise = 2
        # sea_level_rise_vertical_units = "feet"
        # subsidence = 0
        # subsidence_vertical_units = "feet"
        # rainfall_increase = 20
        # storm_frequency_increase = 20
        # economic_growth = 20
        # population_growth = 0
        # population_growth_new = 20
        # population_growth_existing = 20
        # new_development_elevation = 1
        # new_development_elevation_vertical_units = "feet"
        # new_development_elevation_reference = "floodmap"
        # new_development_shape_file = "pop_growth_new_20.shp"
    
    def set_default(self):
        self.value = 0
        self.type = "hazard"