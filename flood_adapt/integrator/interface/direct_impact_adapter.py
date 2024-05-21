import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from flood_adapt.object_model.interface.measures import IBuyout, IElevate, IFloodProof
from flood_adapt.object_model.interface.site import DirectImpactsModel


class DirectImpactsAdapter(ABC):
    """Abstract class holding the blueprints of a Direct Impacts model that can be connected to FloodAdapt.
    This includes methods for pre-processing the model (w.r.t. projections, strategies and events), running the model,
    post-processing the model, reading the results and reading the template model.
    """

    model_name: str
    template_model_path: Path
    output_model_path: Path
    config: DirectImpactsModel

    def __init__(
        self,
        database_path: str,
        impacts_path: str,
        config: DirectImpactsModel,
    ) -> None:
        self.template_model_path = (
            Path(database_path) / "static" / "templates" / self.model_name
        )  # template should be saved in a folder with the mode name
        self.output_model_path = Path(impacts_path).joinpath(self.model_name)
        self.config = config
        self.database_input_path = Path(database_path) / "input"

        # Setup base flood elevation if given
        if config.bfe:
            self.bfe = {}
            if config.bfe.table:
                self.bfe["mode"] = "table"
                self.bfe["table"] = Path(database_path) / "static" / config.bfe.table
            else:
                self.bfe["mode"] = "geom"
            # Map is always needed!
            self.bfe["geom"] = Path(database_path) / "static" / config.bfe.geom
            self.bfe["name"] = config.bfe.field_name

        self._create_model_dir()

    def _create_model_dir(self):
        if not self.output_model_path.is_dir():
            self.output_model_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.output_model_path)
            self.output_model_path.mkdir(parents=True)

    @abstractmethod
    def has_run_check(self) -> bool:
        """Checks if direct impacts model has finished

        Returns
        -------
        boolean
            True if it has run, False if something went wrong
        """
        ...

    @abstractmethod
    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list[str]] = None
    ):
        """Implement economic growth in the Direct Impacts Model exposure. This is only done for building objects (not e.g., roads).
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
