from flood_adapt.object_model.direct_impact import DirectImpact


class Scenario:
    """The Scenario class containing all information on a single scenario."""
    def __init__(self):
        self.direct_impact = DirectImpact()
