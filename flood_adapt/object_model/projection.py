import os
from pathlib import Path

from flood_adapt.object_model.interface.projections import (
    IProjection,
    PhysicalProjection,
    SocioEconomicChange,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class Projection(IProjection):
    """Projection class that holds all the information for a specific projection."""

    def get_physical_projection(self) -> PhysicalProjection:
        return PhysicalProjection(self.attrs.physical_projection)

    def get_socio_economic_change(self) -> SocioEconomicChange:
        return SocioEconomicChange(self.attrs.socio_economic_change)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.attrs.socio_economic_change.new_development_shapefile:
            src_path = resolve_filepath(
                self.dir_name,
                self.attrs.name,
                self.attrs.socio_economic_change.new_development_shapefile,
            )
            path = save_file_to_database(src_path, Path(output_dir))

            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.socio_economic_change.new_development_shapefile = path.name
