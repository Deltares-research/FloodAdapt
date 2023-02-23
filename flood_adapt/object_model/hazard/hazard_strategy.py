from flood_adapt.object_model.strategy import Strategy


class HazardStrategy(Strategy):
    """ Subclass of Strategy describing a strategy with only impact measures
    """
    def __init__(self) -> None:
        super().__init__()

    def set_default(self):
        """ Sets the default values of the Elevate class attributes
        """
        super().set_default()

    def set_measures(self, measures: list):
        """ Sets the actual Measure class list using the list of measure names

        Args:
            measures (list): list of measures names
        """
        super().set_measures(measures)
        # use type of measure to get the associated measure subclass
        self.measures = [ImpactMeasureFactory.get_impact_measure(type).load(config) for type, config in zip(self.measure_types, self.measure_paths)]
    
    def load(self,  config_file: str = None):
        super().load(config_file)
        self.validate()
