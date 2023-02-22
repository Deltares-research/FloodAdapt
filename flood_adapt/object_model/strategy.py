from flood_adapt.object_model.io.config_io import read_config, write_config
from flood_adapt.object_model.validate.config import validate_existence_config_file, validate_content_config_file
from flood_adapt.object_model.measures.elevate import Elevate
from flood_adapt.object_model.measures.measure import Measure
from pathlib import Path
from itertools import combinations

class Strategy:
    """ Strategy class that holds all the information for a specific strategy
    """
    def __init__(self, config_file: str = None, database_path: str = None) -> None:
        self.set_default()
        self.database_path = database_path
        if config_file:
            self.config_file = config_file
            if not self.database_path:
                self.database_path = str(Path(self.config_file).parents[3])

    def set_default(self):
        """ Sets the default values of the Strategy class attributes
        """
        self.name = ""  # Name of the measure
        self.long_name = ""  # Long name of the measure
        self.config_file = None  # path to the configuration file connected with the measure
        self.measures = []  # list of measures names that are used in a strategy
        self.mandatory_keys = ["name", "long_name"]  # mandatory keys in the config file

    def set_name(self, name: str):
        self.name = name
    
    def set_long_name(self, long_name: str):
        self.long_name = long_name
    
    def set_measures(self, measures: list):
        """ Sets the actual Measure class list using the list of measure names

        Args:
            measures (list): list of measures names
        """
        measure_paths = [str(Path(self.database_path, "input", "measures", measure, "{}.toml".format(measure))) for measure in measures]
        # parse measures config files to get type of measure
        types = [read_config(measure_path)["type"] for measure_path in measure_paths]
        # use type of measure to get the associated measure subclass
        self.measures = [measure_parser(type)(config).load() for type, config in zip(types, measure_paths)]

    def load(self):
        """ loads and updates the class attributes from a configuration file
        """
        # Validate the existence of the configuration file
        if validate_existence_config_file(self.config_file):
            config = read_config(self.config_file)

        # Validate that the mandatory keys are in the configuration file
        if validate_content_config_file(config, self.config_file, self.mandatory_keys):
            self.set_name(config["name"])
            self.set_long_name(config["long_name"])
            if "measures" in config.keys():
                self.set_measures(config["measures"])
        
        self.validate()

        return self
    
    def validate(self):
        """ Validates if the combination of measures can happen, since impact measures cannot affect the same properties

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
            msg = "Cannot create strategy! There are ovelapping buildings for which measures are proposed"
            counter = 0
            for i, comb in enumerate(combs):
                if overlapping[i]:
                    if counter > 0:
                        msg += " and"
                    msg += " between measure '{}' and measure '{}'".format(self.measures[comb[0][0]].long_name, self.measures[comb[1][0]].long_name)
                    counter += 1
            raise ValueError(msg)
        

def measure_parser(type: str) -> Measure:
    """ Simple parser to get the respective measure subclass from a measure type string given in the config file

    Args:
        type (str): name of measure type

    Returns:
        Measure: Measure subclass
    """
    if type == "elevate_properties":
        return Elevate