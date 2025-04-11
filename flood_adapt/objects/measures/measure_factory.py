import os
from typing import Union

import tomli

from flood_adapt.objects.measures.measures import (
    Buyout,
    Elevate,
    FloodProof,
    FloodWall,
    GreenInfrastructure,
    Measure,
    MeasureType,
    Pump,
)


class MeasureFactory:
    @staticmethod
    def get_measure_type(filepath: Union[str, os.PathLike]):
        """Get a measure type from toml file."""
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        type = toml.get("type")
        return MeasureType(type)

    @staticmethod
    def get_measure_object(filepath: Union[str, os.PathLike]) -> Measure:
        measure_type = MeasureFactory.get_measure_type(filepath)

        if MeasureType.is_impact(measure_type):
            return ImpactMeasureFactory.get_impact_measure(measure_type).load_file(
                filepath
            )
        elif MeasureType.is_hazard(measure_type):
            return HazardMeasureFactory.get_hazard_measure(measure_type).load_file(
                filepath
            )
        else:
            raise ValueError(f"Measure type {measure_type} not recognized.")


class ImpactMeasureFactory:
    """Simple parser to get the respective measure subclass from a measure type string given in the config file.

    Args:
        type (str): name of measure type

    Returns
    -------
        Measure: Measure subclass
    """

    @staticmethod
    def get_impact_measure(impact_measure: str):
        if impact_measure == "elevate_properties":
            return Elevate
        elif impact_measure == "buyout_properties":
            return Buyout
        elif impact_measure == "floodproof_properties":
            return FloodProof
        else:
            raise ValueError(f"Measure type {impact_measure} not recognized.")


class HazardMeasureFactory:
    """Simple parser to get the respective measure subclass from a measure type string given in the config file.

    Args:
        type (str): name of measure type

    Returns
    -------
        Measure: Measure subclass
    """

    @staticmethod
    def get_hazard_measure(hazard_measure: str):
        if (
            hazard_measure == "floodwall" or hazard_measure == "levee"
        ):  # these should use the same class right?
            return FloodWall
        elif (
            hazard_measure == "water_square"
            or hazard_measure == "total_storage"
            or hazard_measure == "greening"
        ):
            return GreenInfrastructure
        elif hazard_measure == "pump":
            return Pump
        else:
            raise ValueError(f"Measure type {hazard_measure} not recognized.")
