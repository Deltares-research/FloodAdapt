from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.measure_factory import ImpactMeasureFactory
from flood_adapt.object_model.measure_factory import MeasureFactory
from itertools import combinations


class ImpactStrategy(Strategy):
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
        # Keep only impact measure
        self.measure_paths = [path for type, path in zip(self.measure_types, self.measure_paths) if MeasureFactory.get_measure_type(type) == "impact" ]
        self.measure_types = [type for type in self.measure_types if MeasureFactory.get_measure_type(type) == "impact" ]
        # use type of measure to get the associated measure subclass
        self.measures = [ImpactMeasureFactory.get_impact_measure(type).load(config) for type, config in zip(self.measure_types, self.measure_paths)]
    
    def load(self,  config_file: str = None):
        super().load(config_file)
        self.validate()
        
        return self

    def validate(self):
            """ Validates if the combination of ImpactMeasure can happen, since impact measures cannot affect the same properties

            Raises:
                ValueError: information on which combinations of measures have condlicting properties
            """
            # Get ids of objects affected for each measure
            ids = [measure.get_object_ids() for measure in self.measures]

            # Get all possible pairs of measures and check overlapping buildings for each measure
            combs = list(combinations(enumerate(ids), 2))
            common_elements = []
            for comb in combs:
                common_elements.append(list(set(comb[0][1]).intersection(comb[1][1])))

            # If there is any combination with overlapping buildings raise Error and do not allow for Strategy object creation
            overlapping = [len(k)>0 for k in common_elements]
            if any(overlapping):
                msg = "Cannot create strategy! There are overlapping buildings for which measures are proposed"
                counter = 0
                for i, comb in enumerate(combs):
                    if overlapping[i]:
                        if counter > 0:
                            msg += " and"
                        msg += " between measure '{}' and measure '{}'".format(self.measures[comb[0][0]].long_name, self.measures[comb[1][0]].long_name)
                        counter += 1
                raise ValueError(msg)