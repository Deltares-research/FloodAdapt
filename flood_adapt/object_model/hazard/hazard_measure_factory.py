from flood_adapt.object_model.hazard.measure.floodwall import FloodWall


class HazardMeasureFactory:
    """ Simple parser to get the respective measure subclass from a measure type string given in the config file

    Args:
        type (str): name of measure type

    Returns:
        Measure: HazardMeasure subclass
    """
    @staticmethod
    def get_hazard_measure(hazard_measure: str):
        if hazard_measure == "floodwall" or hazard_measure == "levee": # these should use the same class right?
            return FloodWall()
        elif hazard_measure == "pump":
            pass
