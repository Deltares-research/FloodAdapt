
class Scenario:
    """The Scenario class containing all information on a single scenario."""
    def __init__(self):
        self.set_default()

    def set_default(self):
        self.name = ""
        self.long_name = ""
        self.run_type = "event"  # event for a single event and "risk" for a probabilistic event set and risk calculation
        self.has_run_hazard = False
        self.has_run_direct_impact = False
        self.config_file = ""
        self.flood_map_path = ""

