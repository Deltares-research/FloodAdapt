from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from flood_adapt.object_model.interface.measures import IBuyout, IElevate, IFloodProof
from flood_adapt.object_model.interface.site import DirectImpactsModel


class DirectImpactsAdapter(ABC):
    """Class holding the attributes and methods that a Direct Impact model can be connected to FloodAdapt.
    This includes pre-processing the model (w.r.t. projections, strategies and events), running the model,
    post-processing the model, and reading the results.
    """

    name: str
    template_model_root: Path
    model_path: Path
    config: DirectImpactsModel

    def __init__(self):
        pass

    @abstractmethod
    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list[str]] = None
    ):
        """Implement economic growth in the exposure of FIAT. This is only done for buildings.
        This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        economic_growth : float
            Percentage value of economic growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the economic growth on,
            by default None
        """
        ...

    @abstractmethod
    def apply_population_growth_existing(
        self, population_growth: float, ids: Optional[list[str]] = None
    ):
        """Implement population growth in the exposure of FIAT. This is only done for buildings.
        This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        population_growth : float
            Percentage value of population growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        ...

    @abstractmethod
    def apply_population_growth_new(
        self,
        population_growth: float,
        ground_floor_height: float,
        elevation_type: str,
        area_path: str,
        ground_elevation: Union[None, str, Path] = None,
        aggregation_areas: Union[List[str], List[Path], str, Path] = None,
        attribute_names: Union[List[str], str] = None,
        label_names: Union[List[str], str] = None,
    ):
        """Implement population growth in new development area.

        Parameters
        ----------
        population_growth : float
            percentage of the existing population (value of assets) to use for the new area
        ground_floor_height : float
            height of the ground floor to be used for the objects in the new area
        elevation_type : str
            "floodmap" or "datum"
        area_path : str
            path to geometry file with new development areas
        """
        ...

    @abstractmethod
    def elevate_properties(
        self,
        elevate: IElevate,
        ids: Optional[list[str]] = None,
    ):
        """Elevate properties by adjusting the "Ground Floor Height" column
        in the FIAT exposure file.

        Parameters
        ----------
        elevate : Elevate
            this is an "elevate" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to elevate,
            by default None
        """
        ...

    @abstractmethod
    def buyout_properties(self, buyout: IBuyout, ids: Optional[list[str]] = None):
        """Buyout properties by setting the "Max Potential Damage: {}" column to
        zero in the FIAT exposure file.

        Parameters
        ----------
        buyout : Buyout
            this is an "buyout" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on, by default None
        """
        ...

    @abstractmethod
    def floodproof_properties(
        self, floodproof: IFloodProof, ids: Optional[list[str]] = None
    ):
        """Floodproof properties by creating new depth-damage functions and
        adding them in "Damage Function: {}" column in the FIAT exposure file.

        Parameters
        ----------
        floodproof : FloodProof
            this is an "floodproof" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        ...
