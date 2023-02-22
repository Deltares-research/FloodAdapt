from flood_adapt.object_model.direct_impact.socio_economic_change.socio_economic_change import SocioEconomicChange
from flood_adapt.object_model.direct_impact.direct_impact_strategies import DirectImpactStrategies
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.site import SiteConfig
from flood_adapt.object_model.io.config_io import read_config, write_config


class DirectImpact:
    """The Direct Impact class containing all information on a single direct impact scenario."""
    def __init__(self, config_file_path: str):
        self.name = ""
        self.long_name = ""
        self.run_type = "event"  # event for a single event and "risk" for a probabilistic event set and risk calculation
        self.has_run_hazard = False
        self.has_run_direct_impact = False
        self.config_file = config_file_path
        self.flood_map_path = ""
        self.result_path = ""
        self.ensemble = ""
        self.event = ""

    def read(self):
        self.config = read_config(self.config_file)

    def write(self):
        write_config(self.config, "path to write to")  # this is a placeholder for the function to be filled

    def configure(self):
        self.get_configuration()

        self.socio_economic_change = SocioEconomicChange()
        self.direct_impact_strategy = DirectImpactStrategies()
        self.hazard = Hazard()
        self.site_info = SiteConfig()

    def run(self):
        """This function runs the scenario? Shouldn't this be done from the Integrator?
        """
        pass