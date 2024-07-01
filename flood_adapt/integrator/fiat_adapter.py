import gc
from pathlib import Path
from typing import List, Optional, Union

from hydromt_fiat.fiat import FiatModel

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.events import Mode
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength
from flood_adapt.object_model.site import Site


class FiatAdapter:
    """All the attributes of the template fiat model and the methods to adjust it according to the projection and strategy attributes."""

    fiat_model: FiatModel  # hydroMT-FIAT model
    site: Site  # Site model
    bfe_path: Path  # path for the base flood elevation file
    bfe_name: str  # variable name of the base flood elevation

    def __init__(self, model_root: str, database_path: str) -> None:
        """Load FIAT model based on a root directory."""
        # Load FIAT template
        self._logger = FloodAdaptLogging.getLogger(__name__)
        self.fiat_model = FiatModel(root=model_root, mode="r", logger=self._logger)
        self.fiat_model.read()

        # Get site information
        self.site = Site.load_file(
            Path(database_path) / "static" / "site" / "site.toml"
        )
        if self.site.attrs.fiat.bfe:
            self.bfe = {}
            # Get base flood elevation path and variable name
            # if table is given use that, else use the map
            if self.site.attrs.fiat.bfe.table:
                self.bfe["mode"] = "table"
                self.bfe["table"] = (
                    Path(database_path) / "static" / self.site.attrs.fiat.bfe.table
                )
            else:
                self.bfe["mode"] = "geom"
            # Map is always needed!
            self.bfe["geom"] = (
                Path(database_path) / "static" / self.site.attrs.fiat.bfe.geom
            )

            self.bfe["name"] = self.site.attrs.fiat.bfe.field_name

    def __del__(self) -> None:
        for handler in self._logger.handlers:
            handler.close()
        self._logger.handlers.clear()
        # Use garbage collector to ensure file handlers are properly cleaned up
        gc.collect()

    def set_hazard(self, hazard: Hazard) -> None:
        map_fn = hazard.flood_map_path
        map_type = hazard.site.attrs.fiat.floodmap_type
        var = "zsmax" if hazard.event_mode == Mode.risk else "risk_maps"
        is_risk = hazard.event_mode == Mode.risk

        # Add the hazard data to a data catalog with the unit conversion
        wl_current_units = UnitfulLength(value=1.0, units="meters")
        conversion_factor = wl_current_units.convert(self.fiat_model.exposure.unit)

        self.fiat_model.setup_hazard(
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
        ].isin(self.site.attrs.fiat.non_building_names)

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
        ].isin(self.site.attrs.fiat.non_building_names)

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
        objectids = elevate.get_object_ids(self.fiat_model)
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
        ].isin(self.site.attrs.fiat.non_building_names)

        # Get rows that are affected
        objectids = buyout.get_object_ids(self.fiat_model)
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
        objectids = floodproof.get_object_ids(self.fiat_model)
        if ids:
            objectids = [id for id in objectids if id in ids]

        # Use hydromt function
        self.fiat_model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.attrs.elevation.value,
            damage_function_types=["Structure", "Content"],
            vulnerability=self.fiat_model.vulnerability,
        )
