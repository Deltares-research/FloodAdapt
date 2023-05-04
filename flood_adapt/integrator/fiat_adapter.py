from pathlib import Path

from hydromt_fiat.fiat import FiatModel

from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.direct_impact.socio_economic_change import (
    SocioEconomicChange,
)
from flood_adapt.object_model.hazard.hazard import Hazard
from flood_adapt.object_model.site import Site


class FiatAdapter:
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

    def set_hazard(self, hazard: Hazard):
        raise NotImplementedError

    def apply_economic_growth(
        self,
        socio_economic_change: SocioEconomicChange,
    ):
        """Implement economic growth in the exposure of FIAT.
        This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        socio_economic_change : SocioEconomicChange
            Object containing all the attributes describing the changes
        """
        # Get columns that include max damage
        damage_cols = [  # use hydromt function
            c
            for c in self.fiat_model.exposure.exposure_db.columns
            if "Max Potential Damage:" in c
        ]

        # Get objects that are buildings (using site info)
        buildings_rows = ~self.fiat_model.exposure.exposure_db[
            "Primary Object Type"
        ].isin(self.site.attrs.fiat.non_building_names)

        # Update columns using economic growth value
        updated_max_pot_damage = self.fiat_model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + socio_economic_change.attrs.economic_growth / 100.0
        )

        # update fiat model
        self.fiat_model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_existing(
        self, socio_economic_change: SocioEconomicChange
    ):
        """Implement population growth in the exposure of FIAT.
        THis population growth describes the population increase in the same area as before.
        This is done by multiplying maximum potential damages of objects with the percentage increase.

        Parameters
        ----------
        socio_economic_change : SocioEconomicChange
            Object containing all the attributes describing the changes
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

        # Update columns using economic growth value
        updated_max_pot_damage = self.fiat_model.exposure.exposure_db.copy()
        updated_max_pot_damage.loc[buildings_rows, damage_cols] *= (
            1.0 + socio_economic_change.attrs.population_growth_existing / 100.0
        )

        # update fiat model
        self.fiat_model.exposure.update_max_potential_damage(
            updated_max_potential_damages=updated_max_pot_damage
        )

    def apply_population_growth_new(
        self, socio_economic_change: SocioEconomicChange, proj_path: str
    ):
        """Implement population growth in a new area.

        Parameters
        ----------
        socio_economic_change : SocioEconomicChange
            Object containing all the attributes describing the changes
        proj_path : str
            path to where projection is saved
        """
        # Get reference type to align with hydromt
        if socio_economic_change.attrs.new_development_elevation.type == "floodmap":
            elev_ref = "geom"
        elif socio_economic_change.attrs.new_development_elevation.type == "datum":
            elev_ref = "datum"

        # Use hydromt function
        self.fiat_model.exposure.setup_new_composite_areas(
            percent_growth=socio_economic_change.attrs.population_growth_new,
            geom_file=Path(proj_path).joinpath(
                socio_economic_change.attrs.new_development_shapefile
            ),
            ground_floor_height=socio_economic_change.attrs.new_development_elevation.value,
            damage_types=["Structure", "Content"],
            vulnerability=self.fiat_model.vulnerability,
            elevation_reference=elev_ref,
            path_ref=self.bfe_path,
            attr_ref=self.bfe_name,
        )

    def apply_elevate_properties(self, elevate: Elevate):
        """Elevate properties

        Parameters
        ----------
        elevate : Elevate
            _description_
        """
        # Get reference type to align with hydromt
        if elevate.attrs.elevation.type == "floodmap":
            elev_ref = "geom"
        elif elevate.attrs.elevation.type == "datum":
            elev_ref = "datum"

        # Use hydromt function
        self.fiat_model.exposure.raise_ground_floor_height(
            raise_by=elevate.attrs.elevation.value,
            objectids=elevate.get_object_ids(),
            height_reference=elev_ref,
            path_ref=self.bfe_path,
            attr_ref=self.bfe_name,
        )
