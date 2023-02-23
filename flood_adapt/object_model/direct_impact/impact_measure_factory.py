from flood_adapt.object_model.direct_impact.measure.elevate import Elevate


class ImpactMeasureFactory:
    """ Simple parser to get the respective measure subclass from a measure type string given in the config file

    Args:
        type (str): name of measure type

    Returns:
        Measure: ImpactMeasure subclass
    """
    @staticmethod
    def get_impact_measure(impact_measure: str):
        if impact_measure == "elevate_properties":
            return Elevate()
        elif impact_measure == "buyout_properties":
            pass
        elif impact_measure == "floodproof_properties":
            pass