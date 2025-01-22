import logging
from pathlib import Path
from typing import Any, List, Optional, Union

import geopandas as gpd
from hydromt_fiat.fiat import FiatModel

from flood_adapt import unit_system as us
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.direct_impact.measure.measure_helpers import (
    get_object_ids,
)
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.hazard.interface.events import Mode
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.measures import (
    IMeasure,
    MeasureType,
)
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
)
from flood_adapt.object_model.utils import resolve_filepath


class FiatAdapter:  # TODO implement ImpactAdapter interface
    """All the attributes of the template fiat model and the methods to adjust it according to the projection and strategy attributes."""

    fiat_model: FiatModel  # hydroMT-FIAT model
    site: Site  # Site model
    bfe_path: Path  # path for the base flood elevation file
    bfe_name: str  # variable name of the base flood elevation

    def __init__(self, model_root: str, database_path: str) -> None:
        """Load FIAT model based on a root directory."""
        # Load FIAT template
        self.logger = FloodAdaptLogging.getLogger(__name__, level=logging.INFO)
        self.fiat_model = FiatModel(root=model_root, mode="r")
        self.fiat_model.read()

        # Get site information
        self.site = Site.load_file(
            Path(database_path) / "static" / "config" / "site.toml"
        )
        if self.site.attrs.fiat.config.bfe:
            self.bfe = {}
            # Get base flood elevation path and variable name
            # if table is given use that, else use the map
            if self.site.attrs.fiat.config.bfe.table:
                self.bfe["mode"] = "table"
                self.bfe["table"] = (
                    Path(database_path)
                    / "static"
                    / self.site.attrs.fiat.config.bfe.table
                )
            else:
                self.bfe["mode"] = "geom"
            # Map is always needed!
            self.bfe["geom"] = (
                Path(database_path) / "static" / self.site.attrs.fiat.config.bfe.geom
            )

            self.bfe["name"] = self.site.attrs.fiat.config.bfe.field_name

    def close_files(self):
        """Close all open files and clean up file handles."""
        if hasattr(self.logger, "handlers"):
            for handler in self.logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    self.logger.removeHandler(handler)

    def __enter__(self) -> "FiatAdapter":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close_files()
        return False

    def set_hazard(self, floodmap: FloodMap) -> None:
        var = "zsmax" if floodmap.mode == Mode.risk else "risk_maps"
        is_risk = floodmap.mode == Mode.risk

        # Add the floodmap data to a data catalog with the unit conversion
        wl_current_units = us.UnitfulLength(value=1.0, units=us.UnitTypesLength.meters)
        conversion_factor = wl_current_units.convert(self.fiat_model.exposure.unit)

        self.fiat_model.setup_hazard(
            map_fn=floodmap.path,
            map_type=floodmap.type,
            rp=None,
            crs=None,  # change this in new version (maybe to str(floodmap.crs.split(':')[1]))
            nodata=-999,  # change this in new version
            var=var,
            chunks="auto",
            risk_output=is_risk,
            unit_conversion_factor=conversion_factor,
        )

    def apply_economic_growth(
        self, economic_growth: float, ids: Optional[list[str]] = []
    ):
        """Implement economic growth in the exposure of FIAT.

        This is only done for buildings. This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        economic_growth : float
            Percentage value of economic growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the economic growth on,
            by default None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.fiat_model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self.fiat_model.exposure.exposure_db[
                "Object ID"
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self.fiat_model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + economic_growth / 100.0
        )

        # update fiat model
        self.fiat_model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_existing(
        self, population_growth: float, ids: Optional[list[str]] = []
    ):
        """Implement population growth in the exposure of FIAT.

        This is only done for buildings. This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        population_growth : float
            Percentage value of population growth.
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.fiat_model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # If ids are given use that as an additional filter
        if ids:
            buildings_rows = buildings_rows & self.fiat_model.exposure.exposure_db[
                "Object ID"
            ].isin(ids)

        # Update columns using economic growth value
        updated_max_pot_damage = self.fiat_model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + population_growth / 100.0
        )

        # update fiat model
        self.fiat_model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

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
        # Get reference type to align with hydromt
        if elevation_type == "floodmap":
            if not self.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            # Use hydromt function
            self.fiat_model.exposure.setup_new_composite_areas(
                percent_growth=population_growth,
                geom_file=Path(area_path),
                ground_floor_height=ground_floor_height,
                damage_types=["Structure", "Content"],
                vulnerability=self.fiat_model.vulnerability,
                elevation_reference="geom",
                path_ref=self.bfe["geom"],
                attr_ref=self.bfe["name"],
                ground_elevation=ground_elevation,
                aggregation_area_fn=aggregation_areas,
                attribute_names=attribute_names,
                label_names=label_names,
            )
        elif elevation_type == "datum":
            # Use hydromt function
            self.fiat_model.exposure.setup_new_composite_areas(
                percent_growth=population_growth,
                geom_file=Path(area_path),
                ground_floor_height=ground_floor_height,
                damage_types=["Structure", "Content"],
                vulnerability=self.fiat_model.vulnerability,
                elevation_reference="datum",
                ground_elevation=ground_elevation,
                aggregation_area_fn=aggregation_areas,
                attribute_names=attribute_names,
                label_names=label_names,
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def elevate_properties(
        self,
        elevate: Elevate,
        ids: Optional[list[str]] = [],
    ):
        """Elevate properties by adjusting the "Ground Floor Height" column in the FIAT exposure file.

        Parameters
        ----------
        elevate : Elevate
            this is an "elevate" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to elevate,
            by default None
        """
        # If ids are given use that as an additional filter
        objectids = get_object_ids(elevate, self.fiat_model)
        if ids:
            objectids = [id for id in objectids if id in ids]

        # Get reference type to align with hydromt
        if elevate.attrs.elevation.type == "floodmap":
            if not self.bfe:
                raise ValueError(
                    "Base flood elevation (bfe) map is required to use 'floodmap' as reference."
                )
            elev_ref = self.bfe["mode"]
            path_ref = self.bfe[elev_ref]
            # Use hydromt function
            self.fiat_model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference=elev_ref,
                path_ref=path_ref,
                attr_ref=self.bfe["name"],
            )

        elif elevate.attrs.elevation.type == "datum":
            # Use hydromt function
            self.fiat_model.exposure.raise_ground_floor_height(
                raise_by=elevate.attrs.elevation.value,
                objectids=objectids,
                height_reference="datum",
            )
        else:
            raise ValueError("elevation type can only be one of 'floodmap' or 'datum'")

    def buyout_properties(self, buyout: Buyout, ids: Optional[list[str]] = []):
        """Buyout properties by setting the "Max Potential Damage: {}" column to zero in the FIAT exposure file.

        Parameters
        ----------
        buyout : Buyout
            this is an "buyout" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on, by default None
        """
        # Get columns that include max damage
        damage_cols = [
            c
            for c in self.fiat_model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.config.non_building_names)

        # Get rows that are affected
        objectids = get_object_ids(buyout, self.fiat_model)
        rows = (
            self.fiat_model.exposure.exposure_db["Object ID"].isin(objectids)
            & buildings_rows
        )

        # If ids are given use that as an additional filter
        if ids:
            rows = self.fiat_model.exposure.exposure_db["Object ID"].isin(ids) & rows

        # Update columns using economic growth value
        updated_max_pot_damage = self.fiat_model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[rows, damage_cols] *= 0

        # update fiat model
        self.fiat_model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def floodproof_properties(
        self, floodproof: FloodProof, ids: Optional[list[str]] = []
    ):
        """Floodproof properties by creating new depth-damage functions and adding them in "Damage Function: {}" column in the FIAT exposure file.

        Parameters
        ----------
        floodproof : FloodProof
            this is an "floodproof" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        # If ids are given use that as an additional filter
        objectids = get_object_ids(floodproof, self.fiat_model)
        if ids:
            objectids = [id for id in objectids if id in ids]

        # Use hydromt function
        self.fiat_model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.attrs.elevation.value,
            damage_function_types=["Structure", "Content"],
            vulnerability=self.fiat_model.vulnerability,
        )

    def get_buildings(self) -> gpd.GeoDataFrame:
        if self.fiat_model.exposure is None:
            raise ValueError(
                "FIAT model does not have exposure, make sure your model has been initialized."
            )
        return self.fiat_model.exposure.select_objects(
            primary_object_type="ALL",
            non_building_names=self.site.attrs.fiat.config.non_building_names,
            return_gdf=True,
        )

    def get_property_types(self) -> list:
        if self.fiat_model.exposure is None:
            raise ValueError(
                "FIAT model does not have exposure, make sure your model has been initialized."
            )

        types = self.fiat_model.exposure.get_primary_object_type()
        if types is None:
            raise ValueError("No property types found in the FIAT model.")
        types.append("all")  # Add "all" type for using as identifier

        names = self.site.attrs.fiat.config.non_building_names
        if names:
            for name in names:
                if name in types:
                    types.remove(name)

        return types

    def get_object_ids(
        self,
        measure: IMeasure,
    ) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        if not MeasureType.is_impact(measure.attrs.type):
            raise ValueError(
                f"Measure type {measure.attrs.type} is not an impact measure. "
                "Can only retrieve object ids for impact measures."
            )

        # check if polygon file is used, then get the absolute path
        if measure.attrs.polygon_file:
            polygon_file = resolve_filepath(
                object_dir=ObjectDir.measure,
                obj_name=measure.attrs.name,
                path=measure.attrs.polygon_file,
            )
        else:
            polygon_file = None

        # use the hydromt-fiat method to the ids
        ids = self.fiat_model.exposure.get_object_ids(
            selection_type=measure.attrs.selection_type,
            property_type=measure.attrs.property_type,
            non_building_names=self.site.attrs.fiat.config.non_building_names,
            aggregation=measure.attrs.aggregation_area_type,
            aggregation_area_name=measure.attrs.aggregation_area_name,
            polygon_file=str(polygon_file),
        )

        return ids
