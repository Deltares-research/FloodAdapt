from flood_adapt.object_model.direct_impact.socio_economic_change.socio_economic_change import SocioEconomicChange
# from flood_adapt.object_model.direct_impact.direct_impact_strategies import DirectImpactStrategies
# from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.validate.config import validate_content_config_file, validate_existence_config_file
from flood_adapt.object_model.io.database_io import DatabaseIO


class DirectImpacts:
    """The Direct Impact class containing all information on a single direct impact scenario."""
    def __init__(self, database_path: str, site_name: str):
        self.name = ""
        self.long_name = ""
        self.site_name = site_name
        self.run_type = "event"  # event for a single event and "risk" for a probabilistic event set and risk calculation
        self.has_run_hazard = False
        self.has_run_direct_impact = False
        self.database_path = database_path
        self.flood_map_path = ""  # To be determined what type this object is, depending on how it will get it from the Events class.
        self.result_path = ""
        self.mandatory_keys = ["name", "long_name", "projection", "event", "strategy"]

        self.database = DatabaseIO()

    def write(self):
        write_config(self.config, "path to write to")  # this is a placeholder for the function to be filled

    def set_name(self, value: str):
        self.name = value
    
    def set_long_name(self, value: str):
        self.long_name = value

    def set_run_type(self, value: str):
        self.run_type = value

    def set_has_run_hazard(self, value: bool):
        self.has_run_hazard = value
    
    def set_has_run_direct_impact(self, value: bool):
        self.has_run_direct_impact = value
        
    def set_flood_map_path(self, value: str):
        self.flood_map_path = value
    
    def set_result_path(self, value: str):
        self.result_path = value
        
    def set_ensemble(self, value: str):
        self.ensemble = value
        
    def set_event(self, value: str):
        self.result_path = value

    def load(self, config_file_path: str):
        self.config_file = config_file_path
        if validate_existence_config_file(self.config_file):
            self.config = read_config(self.config_file)
        
        if validate_content_config_file(self.config, self.config_file, self.mandatory_keys):
            self.set_name(self.config["name"])
            self.set_long_name(self.config["long_name"])

        self.socio_economic_change = SocioEconomicChange()
        # self.direct_impact_strategy = DirectImpactStrategies()
        # self.hazard = Hazard()
        # self.hazard.set_values(self.config)

    def run(self):
        """This function runs the scenario? Shouldn't this be done from the Integrator?
        """
        pass
