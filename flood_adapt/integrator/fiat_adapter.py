import gc
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

from geopandas import GeoDataFrame
from hydromt.log import setuplog
from hydromt_fiat.fiat import FiatModel

import flood_adapt.config as FloodAdapt_config
from flood_adapt.integrator.interface.direct_impacts_adapter import DirectImpactsAdapter
from flood_adapt.object_model.interface.measures import (
    IBuyout,
    IElevate,
    IFloodProof,
    ImpactMeasureModel,
)
from flood_adapt.object_model.interface.site import Floodmap_type
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength
from flood_adapt.object_model.utils import cd


class FiatAdapter(DirectImpactsAdapter):
    """Implementation of a DirectImpactsAdapter class for a Delft-FIAT model including
    all the methods for reading and writing model data, and adjusting the model based
    on scenarios.
    """

    model_name = "fiat"  # model's name

    def _read_template_model(self):
        """
        Reads the template FIAT model.

        This method initializes the logger and reads the template FIAT model
        using the provided model path.

        Args:
            None

        Returns:
            None
        """
        self.logger = setuplog("hydromt_fiat", log_level=10)
        self.model = FiatModel(
            root=self.template_model_path, mode="r", logger=self.logger
        )
        self.model.read()

    def close_model(self) -> None:
        """
        Closes the model and the associated logger.

        This method closes the fiat_logger by closing all its handlers and deletes the model object.

        Returns:
            None
        """
        # Close fiat_logger
        for handler in self.logger.handlers:
            handler.close()
        self.logger.handlers.clear()
        # Use garbage collector to ensure file handlers are properly cleaned up
        gc.collect()
        del self.model

    def get_building_locations(self) -> GeoDataFrame:
        """
        Retrieves the locations of all buildings from the template model.

        Returns:
            GeoDataFrame: A GeoDataFrame containing the locations of buildings.
        """
        buildings = self.model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.config.non_building_names,
            return_gdf=True,
        )

        return buildings

    def get_building_types(self) -> list[str]:
        """
        Retrieves the list of building types from the model's exposure data.

        Returns:
            A list of building types, excluding the ones specified in the config.non_building_names.
        """
        types = self.model.exposure.get_primary_object_type()
        for name in self.config.non_building_names:
            if name in types:
                types.remove(name)
        # Add "all" type for using as identifier
        types.append("all")

        return types

    def get_building_ids(self) -> list[int]:
        """
        Retrieves the IDs of all existing buildings in the FIAT model.

        Returns:
            list: A list of buildings IDs.
        """
        # Get ids of existing buildings
        ids = self.model.exposure.get_object_ids(
            "all", non_building_names=self.config.non_building_names
        )
        return ids

    def get_measure_building_ids(self, attrs: ImpactMeasureModel) -> list[int]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """

        # use the hydromt-fiat method to the ids
        ids = self.model.exposure.get_object_ids(
            selection_type=attrs.selection_type,
            property_type=attrs.property_type,
            non_building_names=self.config.non_building_names,
            aggregation=attrs.aggregation_area_type,
            aggregation_area_name=attrs.aggregation_area_name,
            polygon_file=attrs.polygon_file,
        )

        return ids

    def has_run_check(self) -> bool:
        """Checks if direct impacts model has finished

        Returns
        -------
        boolean
            True if the FIAT model has finished running successfully, False otherwise
        """
        log_file = self.output_model_path.joinpath("fiat.log")
        if log_file.exists():
            with open(log_file, "r", encoding="cp1252") as f:
                if "Geom calculation are done!" in f.read():
                    return True
                else:
                    return False
        else:
            return False

    def set_hazard(
        self,
        map_fn: str,
        map_type: Floodmap_type,
        var: str,
        is_risk: bool,
        units: str = "meters",
    ) -> None:
        # map_fn: str, map_type: Floodmap_type , var: str, is_risk: bool, units: str = "meters"
        """
        Sets the hazard data for the model.

        Args:
            hazard (Hazard): The hazard object containing the necessary information.

        Returns:
            None
        """
        # Add the hazard data to a data catalog with the unit conversion
        wl_current_units = UnitfulLength(value=1.0, units=units)
        conversion_factor = wl_current_units.convert(self.model.exposure.unit)

        self.model.setup_hazard(
            map_fn=map_fn,
            map_type=map_type,
            rp=None,
            crs=None,  # change this in new version
            nodata=-999,  # change this in new version
            var=var,
            chunks="auto",
            risk_output=is_risk,
            unit_conversion_factor=conversion_factor,
        )

    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list] = None
    ) -> None:
        """
        Applies economic growth to the maximum potential damage of buildings.

        Args:
            economic_growth (float): The economic growth rate in percentage.
            ids (Optional[list]): Optional list of building IDs to apply the economic growth to.

        Returns:
            None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.model.exposure.exposure_db["Primary Object Type"].isin(
            self.config.non_building_names
        )

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self.model.exposure.exposure_db[
                "Object ID"
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self.model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + economic_growth / 100.0
        )

        # update fiat model
        self.model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_existing(
        self, population_growth: float, ids: Optional[list[str]] = None
    ) -> None:
        """
        Applies population growth to the existing maximum potential damage values for buildings.

        Args:
            population_growth (float): The percentage of population growth.
            ids (Optional[list[str]]): Optional list of building IDs to apply the population growth to.

        Returns:
            None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.model.exposure.exposure_db["Primary Object Type"].isin(
            self.config.non_building_names
        )

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self.model.exposure.exposure_db[
                "Object ID"
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self.model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + population_growth / 100.0
        )

        # update fiat model
        self.model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_new(
        self,
        population_growth: float,
        ground_floor_height: float,
        elevation_type: str,
        area_path: str,
        ground_elevation: Union[None, str, Path] = None,
    ) -> None:
        """
        Applies population growth to the model's exposure data.

        Args:
            population_growth (float): The percentage population growth.
            ground_floor_height (float): The height of the ground floor.
            elevation_type (str): The type of elevation reference. Can be 'floodmap' or 'datum'.
            area_path (str): The path to the area file.
            ground_elevation (Union[None, str, Path], optional): The ground elevation. Defaults to None.
            aggregation_areas (Union[List[str], List[Path], str, Path], optional): The aggregation areas. Defaults to None.
            attribute_names (Union[List[str], str], optional): The attribute names. Defaults to None.
            label_names (Union[List[str], str], optional): The label names. Defaults to None.

        Raises:
            ValueError: If elevation_type is not 'floodmap' or 'datum'.

        Returns:
            None
        """
        # Get reference type to align with hydromt
        if elevation_type == "floodmap":
            if not self.config.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            kwargs = {
                "elevation_reference": "geom",
                "path_ref": self.config.bfe.geom,
                "attr_ref": self.config.bfe.field_name,
            }
        elif elevation_type == "datum":
            kwargs = {"elevation_reference": "datum"}
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")
        # Get aggregation areas info
        aggregation_areas = [aggr.file for aggr in self.config.aggregation]
        attribute_names = [aggr.field_name for aggr in self.config.aggregation]
        label_names = [
            f"Aggregation Label: {aggr.name}" for aggr in self.config.aggregation
        ]
        # Use hydromt function
        self.model.exposure.setup_new_composite_areas(
            percent_growth=population_growth,
            geom_file=Path(area_path),
            ground_floor_height=ground_floor_height,
            damage_types=["Structure", "Content"],
            vulnerability=self.model.vulnerability,
            ground_elevation=ground_elevation,
            aggregation_area_fn=aggregation_areas,
            attribute_names=attribute_names,
            label_names=label_names,
            **kwargs,
        )

    def elevate_properties(self, elevate: IElevate) -> None:
        """
        Elevates the properties of selected buildings based on the provided elevation information.

        Args:
            elevate (IElevate): An object containing the elevation information.

        Raises:
            ValueError: If the elevation type is neither 'floodmap' nor 'datum'.

        Returns:
            None
        """

        # Get the ids of the buildings that are affected by the selection type
        objectids = self.get_measure_building_ids(elevate.attrs)

        # Get reference type to align with hydromt
        if elevate.attrs.elevation.type == "floodmap":
            if not self.config.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            if self.config.bfe.table:
                path_ref = self.config.bfe.table
                height_reference = "table"
            else:
                path_ref = self.config.bfe.geom
                height_reference = "geom"
            # Use hydromt function
            self.model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference=height_reference,
                path_ref=path_ref,
                attr_ref=self.config.bfe.field_name,
            )

        elif elevate.attrs.elevation.type == "datum":
            # Use hydromt function
            self.model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference="datum",
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def buyout_properties(self, buyout: IBuyout) -> None:
        """
        Buys out properties based on the provided buyout object.

        Args:
            buyout (IBuyout): The buyout object containing information about the properties to be bought out.

        Returns:
            None
        """

        # Get the ids of the buildings that are affected by the selection type
        objectids = self.get_measure_building_ids(buyout.attrs)

        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get rows that are affected
        rows = self.model.exposure.exposure_db["Object ID"].isin(objectids)

        # Update columns using economic growth value
        updated_max_pot_damage = self.model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[rows, damage_cols] *= 0

        # update fiat model
        self.model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def floodproof_properties(self, floodproof: IFloodProof) -> None:
        """
        Floodproofs the properties based on the provided floodproof object.

        Args:
            floodproof (IFloodProof): The floodproof object containing the floodproofing attributes.

        Returns:
            None
        """
        # Get the ids of the buildings that are affected by the selection type
        objectids = self.get_measure_building_ids(floodproof.attrs)

        # Use hydromt function
        self.model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.attrs.elevation.value,
            damage_function_types=["Structure", "Content"],
            vulnerability=self.model.vulnerability,
        )

    def write_model(self) -> None:
        """
        Writes the model to the output model path.

        This method creates the model directory if it doesn't exist,
        sets the root of the model to the output model path, and
        writes the model.

        Returns:
            None
        """
        self._create_output_model_dir
        self.model.set_root(self.output_model_path)
        self.model.write()

    def run(self) -> int:
        """
        Runs the FIAT model.

        Raises:
            ValueError: If the SYSTEM_FOLDER environment variable is not set.

        Returns:
            int: The return code of the process.
        """
        if not FloodAdapt_config.get_system_folder():
            raise ValueError(
                """
                SYSTEM_FOLDER environment variable is not set. Set it by calling FloodAdapt_config.set_system_folder() and provide the path.
                The path should be a directory containing folders with the model executables
                """
            )
        fiat_exec = FloodAdapt_config.get_system_folder() / "fiat" / "fiat.exe"

        with cd(self.output_model_path):
            with open(self.output_model_path.joinpath("fiat.log"), "a") as log_handler:
                process = subprocess.run(
                    f'"{fiat_exec}" run settings.toml',
                    stdout=log_handler,
                    check=True,
                    shell=True,
                )

        return process.returncode

    def write_csv_results(self, csv_path) -> None:
        """
        Writes the output CSV file to the specified path.

        Parameters:
            csv_path (str): The path where the CSV file should be written.

        Returns:
            None
        """
        shutil.copy(self.output_model_path.joinpath("output", "output.csv"), csv_path)
