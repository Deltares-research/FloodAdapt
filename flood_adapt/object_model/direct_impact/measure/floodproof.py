import os
from pathlib import Path

from flood_adapt.object_model.interface.measures import FloodProofModel, IMeasure
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class FloodProof(IMeasure[FloodProofModel]):
    """Subclass of ImpactMeasure describing the measure of flood-proof buildings."""

    _attrs_type = FloodProofModel

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.attrs.polygon_file:
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name
