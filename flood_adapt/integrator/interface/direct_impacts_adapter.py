import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

from geopandas import GeoDataFrame

from flood_adapt.object_model.interface.measures import (
    IBuyout,
    IElevate,
    IFloodProof,
    ImpactMeasureModel,
)
from flood_adapt.object_model.interface.site import DirectImpactsModel


class DirectImpactsAdapter(ABC):
    """Abstract class holding the blueprints for a Direct Impacts model that can be connected to FloodAdapt.

    This includes methods for pre-processing the model (w.r.t. projections, strategies and events), running the model,
    post-processing the model, reading the results and reading the template model.
    """

    model_name: str  # name of the model used

    def __init__(
        self,
        template_model_path: str,
        config: DirectImpactsModel,
        output_model_path: str = None,
    ) -> None:
        """
        Initialize the DirectImpactsAdapter class.

        Args:
            database_path (str): The path to the database.
            config (DirectImpactsModel): The configuration for the direct impacts model.
            impacts_path (str, optional): The path to the impacts location. Defaults to None.
        """
        self.template_model_path = Path(template_model_path)
        self.config = config
        if (
            output_model_path
        ):  # if impacts_path is given, an output location can be generated
            self.output_model_path = Path(output_model_path)
        # read in the template model
        self._read_template_model()

    def _create_output_model_dir(self) -> None:
        """
        Create the output model directory if it doesn't exist.

        If the directory already exists, it removes it and creates a new one.
        """
        if not self.output_model_path.is_dir():
            self.output_model_path.mkdir(parents=True)
        else:
            shutil.rmtree(self.output_model_path)
            self.output_model_path.mkdir(parents=True)

    @abstractmethod
    def _read_template_model(self) -> None:
        """Read the template direct impacts model."""
        ...

    @abstractmethod
    def get_building_locations(self) -> GeoDataFrame:
        """
        Retrieve the locations of all buildings from the template model.

        Returns
        -------
            GeoDataFrame: A GeoDataFrame containing the locations of buildings.
        """
        ...

    @abstractmethod
    def get_building_types(self) -> list[str]:
        """
        Retrieve the list of building types from the model's exposure data.

        Returns
        -------
            A list of building types, excluding the ones specified in the config.non_building_names.
        """
        ...

    @abstractmethod
    def get_building_ids(self) -> list[int]:
        """
        Retrieve the IDs of all existing buildings in the direct impacts model.

        Returns
        -------
            list: A list of buildings IDs.
        """
        ...

    @abstractmethod
    def get_measure_building_ids(self, attrs: ImpactMeasureModel) -> list[int]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        ...

    @abstractmethod
    def has_run_check(self) -> bool:
        """Check if direct impacts model has finished.

        Returns
        -------
        boolean
            True if the direct impacts model has finished running successfully, False otherwise
        """
        ...

    @abstractmethod
    def set_hazard(self, hazard) -> None:
        """
        Set the hazard data for the model.

        Args:
            hazard (Hazard): The hazard object containing the necessary information.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list] = None
    ) -> None:
        """
        Apply economic growth to the maximum potential damage of buildings.

        Args:
            economic_growth (float): The economic growth rate in percentage.
            ids (Optional[list]): Optional list of building IDs to apply the economic growth to.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def apply_population_growth_existing(
        self, population_growth: float, ids: Optional[list[str]] = None
    ) -> None:
        """
        Apply population growth to the existing maximum potential damage values for buildings.

        Args:
            population_growth (float): The percentage of population growth.
            ids (Optional[list[str]]): Optional list of building IDs to apply the population growth to.

        Returns
        -------
            None
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
    ) -> None:
        """
        Apply population growth to the model's exposure data.

        Args:
            population_growth (float): The percentage population growth.
            ground_floor_height (float): The height of the ground floor.
            elevation_type (str): The type of elevation reference. Can be 'floodmap' or 'datum'.
            area_path (str): The path to the area file.
            ground_elevation (Union[None, str, Path], optional): The ground elevation. Defaults to None.
            aggregation_areas (Union[List[str], List[Path], str, Path], optional): The aggregation areas. Defaults to None.
            attribute_names (Union[List[str], str], optional): The attribute names. Defaults to None.
            label_names (Union[List[str], str], optional): The label names. Defaults to None.

        Raises
        ------
            ValueError: If elevation_type is not 'floodmap' or 'datum'.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def elevate_properties(self, elevate: IElevate) -> None:
        """
        Elevates the properties of selected buildings based on the provided elevation information.

        Args:
            elevate (IElevate): An object containing the elevation information.

        Raises
        ------
            ValueError: If the elevation type is neither 'floodmap' nor 'datum'.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def buyout_properties(self, buyout: IBuyout) -> None:
        """
        Buys out properties based on the provided buyout object.

        Args:
            buyout (IBuyout): The buyout object containing information about the properties to be bought out.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def floodproof_properties(self, floodproof: IFloodProof) -> None:
        """
        Floodproofs the properties based on the provided floodproof object.

        Args:
            floodproof (IFloodProof): The floodproof object containing the floodproofing attributes.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def write_model(self) -> None:
        """
        Write the model to the output model path.

        This method creates the model directory if it doesn't exist,
        sets the root of the model to the output model path, and
        writes the model.

        Returns
        -------
            None
        """
        ...

    @abstractmethod
    def run(self, exec_path: str) -> int:
        """
        Run the direct impacts model.

        Raises
        ------
            ValueError: If the SYSTEM_FOLDER environment variable is not set.

        Returns
        -------
            int: The return code of the process.
        """
        ...

    @abstractmethod
    def write_csv_results(self, csv_path) -> None:
        """
        Write the output CSV file to the specified path.

        Parameters
        ----------
            csv_path (str): The path where the CSV file should be written.

        Returns
        -------
            None
        """
        ...
