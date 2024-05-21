from abc import ABC, abstractmethod

from flood_adapt.object_model.models.measures import HazardType, ImpactType
from flood_adapt.object_model.object_classes.measure.hazard_measure.floodwall import (
    FloodWall,
)
from flood_adapt.object_model.object_classes.measure.hazard_measure.green_infrastructure import (
    GreenInfrastructure,
)
from flood_adapt.object_model.object_classes.measure.hazard_measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.object_classes.measure.hazard_measure.pump import Pump
from flood_adapt.object_model.object_classes.measure.impact_measure.buyout import Buyout
from flood_adapt.object_model.object_classes.measure.impact_measure.elevate import (
    Elevate,
)
from flood_adapt.object_model.object_classes.measure.impact_measure.floodproof import (
    FloodProof,
)
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.object_classes.measure.measure import Measure


class IMeasureFactory(ABC):
    """Factory class to get the respective measure subclass from a measure type string given in the config file"""

    @staticmethod
    @abstractmethod
    def get_sub_measure(measure: Measure, data: dict) -> Measure:
        """Simple parser to get the respective measure subclass from a measure type string given in the config file

        Parameters
        ----------
        measure : Measure
            measure type

        Returns
        -------
        Measure
            Measure subclass
        """
        pass

    @staticmethod
    @abstractmethod
    def list_types() -> list:
        """List all measure types

        Returns
        -------
        list
            list of measure types
        """
        pass

class ImpactMeasureFactory(IMeasureFactory):
    """Factory class to get the respective measure sub-subclass from an impact measure type string given in the config file"""

    @staticmethod
    def get_sub_measure(impact_measure: str, data: dict) -> ImpactMeasure:
        """Simple parser to get the respective measure subclass from a measure type string given in the config file

        Parameters
        ----------
        impact_measure : str
            name of measure type
        data : dict
            dictionary with data to load the measure

        Returns
        -------
        Measure
            ImpactMeasure subclass
        """
        if impact_measure == "elevate_properties":
            return Elevate.load_dict(data)
        elif impact_measure == "buyout_properties":
            return Buyout.load_dict(data)
        elif impact_measure == "floodproof_properties":
            return FloodProof.load_dict(data)

    @staticmethod
    def list_types() -> list:
        """List all impact measure types

        Returns
        -------
        list
            list of impact measure types
        """
        return list(ImpactType)


class HazardMeasureFactory(IMeasureFactory):
    """Factory class to get the respective measure sub-subclass from a hazard measure type string given in the config file"""

    @staticmethod
    def get_sub_measure(hazard_measure: str, data: dict) -> HazardMeasure:
        """Simple parser to get the respective measure subclass from a measure type string given in the config file

        Parameters
        ----------
        hazard_measure : str
            name of measure type
        data : dict
            dictionary with data to load the measure

        Returns
        -------
        Measure
            HazardMeasure subclass
        """
        if (
            hazard_measure == "floodwall" or hazard_measure == "levee"
        ):  # these should use the same class right?
            return FloodWall.load_dict(data)
        elif (
            hazard_measure == "water_square"
            or hazard_measure == "total_storage"
            or hazard_measure == "greening"
        ):
            return GreenInfrastructure.load_dict(data)
        elif hazard_measure == "pump":
            return Pump.load_dict(data)

    @staticmethod
    def list_types()->list:
        """List all hazard measure types

        Returns
        -------
        list
            list of hazard measure types
        """
        return list(HazardType)


class MeasureFactory(IMeasureFactory):
    """Factory class to get the respective measure subclass from a measure type string given in the config file"""

    @staticmethod
    def get_sub_measure(
        measure: Measure, data: dict
    ) -> Measure:
        """Simple parser to get the respective measure subclass from a measure type string given in the config file

        Parameters
        ----------
        measure : Measure
            measure type
        data : dict
            dictionary with data to load the measure

        Returns
        -------
        Measure
            Measure subclass
        """
        subtype = measure.get_measure_type()

        if subtype in ImpactMeasureFactory.list_types():
            return ImpactMeasureFactory.get_sub_measure(
                subtype,
                data,
            )

        elif subtype in HazardMeasureFactory.list_types():
            return HazardMeasureFactory.get_sub_measure(
                subtype,
                data,
            )
        
    @staticmethod
    def list_types():
        """List all measure types

        Returns
        -------
        list
            list of measure types
        """
        return ImpactMeasureFactory.list_types() + HazardMeasureFactory.list_types()
