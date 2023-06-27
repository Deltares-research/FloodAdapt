import os
from typing import Union

from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.measure.floodwall import FloodWall
from flood_adapt.object_model.hazard.measure.green_infrastructure import (
    GreenInfraStructure,
)
from flood_adapt.object_model.interface.measures import HazardType, ImpactType
from flood_adapt.object_model.measure import Measure


class MeasureFactory:
    @staticmethod
    def get_measure_object(filepath: Union[str, os.PathLike]):
        measure_type = Measure.get_measure_type(filepath)

        if measure_type in iter(ImpactType):
            return ImpactMeasureFactory.get_impact_measure(measure_type).load_file(
                filepath
            )

        elif measure_type in iter(HazardType):
            return HazardMeasureFactory.get_hazard_measure(measure_type).load_file(
                filepath
            )


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
            return Elevate
        elif impact_measure == "buyout_properties":
            return Buyout
        elif impact_measure == "floodproof_properties":
            return FloodProof


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
            return FloodWall
        elif hazard_measure == "green_infrastructure":
            return GreenInfraStructure
        elif hazard_measure == "pump":
            pass
