import os
from pathlib import Path

from flood_adapt.object_model.interface.measures import (
    FloodWallModel,
    IMeasure,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class FloodWall(IMeasure[FloodWallModel]):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height."""

    _attrs_type = FloodWallModel

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        if self.attrs.polygon_file:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name
