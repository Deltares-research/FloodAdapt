from flood_adapt.object_model.direct_impact.measure.elevate import Elevate

from flood_adapt.object_model.hazard.measure.floodwall import FloodWall


class MeasureFactory:
    @staticmethod
    def get_measure_type(measure: str):
        if measure == "elevate_properties":
            return "impact"
        elif measure == "buyout_properties":
            return "impact"
        elif measure == "floodproof_properties":
            return "impact"
        elif measure == "floodwall":
            return "hazard"
        elif measure == "levee":
            return "hazard"
        elif measure == "pump":
            return "hazard"


class ImpactMeasureFactory:
    """Simple parser to get the respective measure subclass from a measure type string given in the config file

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


class HazardMeasureFactory:
    """Simple parser to get the respective measure subclass from a measure type string given in the config file

    Args:
        type (str): name of measure type

    Returns:
        Measure: HazardMeasure subclass
    """

    @staticmethod
    def get_hazard_measure(hazard_measure: str):
        if (
            hazard_measure == "floodwall" or hazard_measure == "levee"
        ):  # these should use the same class right?
            return FloodWall()
        elif hazard_measure == "pump":
            pass
