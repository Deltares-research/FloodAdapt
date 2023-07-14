import os
from pathlib import Path
from typing import List, Optional, Union

from hydromt_fiat.fiat import FiatModel

from flood_adapt.object_model.direct_impact.measure.buyout import Buyout
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.measure.floodproof import FloodProof
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.interface.events import Mode
from flood_adapt.object_model.site import Site


class FiatAdapter:
    """Class holding all the attributes of the template fiat model and
    the methods to adjust it according to the projection and strategy
    attributes.
    """

    fiat_model: FiatModel  # hydroMT-FIAT model
    site: Site  # Site model
    bfe_path: Path  # path for the base flood elevation file
    bfe_name: str  # variable name of the base flood elevation

    def __init__(self, model_root: str, database_path: str) -> None:
        """Loads FIAT model based on a root directory."""
        # Load FIAT template
        self.fiat_model = FiatModel(root=model_root, mode="r")
        self.fiat_model.read()

        # Get site information
        self.site = Site.load_file(
            Path(database_path) / "static" / "site" / "site.toml"
        )

        # Get base flood elevation path and variable name
        self.bfe_path = Path(database_path) / "static" / "bfe" / "bfe.geojson"
        self.bfe_name = "bfe"

    def set_hazard(self, hazard: Hazard) -> None:
        map_fn = self._get_sfincs_map_path(hazard)
        map_type = hazard.site.attrs.fiat.floodmap_type
        var = "zsmax" if hazard.event_mode == Mode.risk else "risk_maps"
        is_risk = hazard.event_mode == Mode.risk

        self.fiat_model.setup_hazard(
            map_fn=map_fn,
            map_type=map_type,
            rp=None,  # change this in new version
            crs=None,  # change this in new version
            nodata=-999,  # change this in new version
            var=var,
            chunks="auto",
            name_catalog=None,
            risk_output=is_risk,
        )

    def _get_sfincs_map_path(self, hazard: Hazard) -> List[Union[str, Path]]:
        map_path = hazard.sfincs_map_path
        mode = hazard.event_mode
        map_fn: List[Union[str, Path]] = []

        if mode == Mode.single_event:
            map_fn.append(map_path.joinpath("sfincs_map.nc"))

        elif mode == Mode.risk:
            # check for netcdf
            map_fn.extend(
                map_path.joinpath(file)
                for file in os.listdir(str(map_path))
                if file.endswith(".nc")
            )
        return map_fn

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
            elev_ref = "geom"
        elif elevation_type == "datum":
            elev_ref = "datum"

        # Use hydromt function
        self.fiat_model.exposure.setup_new_composite_areas(
            percent_growth=population_growth,
            geom_file=Path(area_path),
            ground_floor_height=ground_floor_height,
            damage_types=["Structure", "Content"],
            vulnerability=self.fiat_model.vulnerability,
            elevation_reference=elev_ref,
            path_ref=self.bfe_path,
            attr_ref=self.bfe_name,
        )

    def elevate_properties(self, elevate: Elevate, ids: Optional[list[str]] = None):
        """Elevate properties by adjusting the "Ground Floor Height" column
        in the FIAT exposure file.

        Parameters
        ----------
        elevate : Elevate
            this is an "elevate" impact measure object
        ids : Optional[list[str]], optional
            List of FIAT "Object ID" values to apply the population growth on,
            by default None
        """
        # Get reference type to align with hydromt
        if elevate.attrs.elevation.type == "floodmap":
            elev_ref = "geom"
        elif elevate.attrs.elevation.type == "datum":
            elev_ref = "datum"

        # If ids are given use that as an additional filter
        objectids = elevate.get_object_ids()
        if ids:
            objectids = [id for id in objectids if id in ids]

        # Use hydromt function
        self.fiat_model.exposure.raise_ground_floor_height(
            raise_by=elevate.attrs.elevation.value,
            objectids=objectids,
            height_reference=elev_ref,
            path_ref=self.bfe_path,
            attr_ref=self.bfe_name,
        )

    def buyout_properties(self, buyout: Buyout, ids: Optional[list[str]] = None):
        """Buyout properties by setting the "Max Potential Damage: {}" column to
        zero in the FIAT exposure file.

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
        objectids = buyout.get_object_ids()
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
        self, floodproof: FloodProof, ids: Optional[list[str]] = None
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
        # If ids are given use that as an additional filter
        objectids = floodproof.get_object_ids()
        if ids:
            objectids = [id for id in objectids if id in ids]

        # Use hydromt function
        self.fiat_model.exposure.truncate_damage_function(
            objectids=objectids,
            floodproof_to=floodproof.attrs.elevation.value,
            damage_function_types=["Structure", "Content"],
            vulnerability=self.fiat_model.vulnerability,
        )
