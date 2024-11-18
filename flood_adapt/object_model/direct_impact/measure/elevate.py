import os
from pathlib import Path
from typing import Any

from flood_adapt.object_model.interface.measures import ElevateModel, ImpactMeasure
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class Elevate(ImpactMeasure[ElevateModel]):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height."""

    attrs: ElevateModel

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, ElevateModel):
            self.attrs = data
        else:
            self.attrs = ElevateModel.model_validate(data)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save the additional files to the database."""
        if self.attrs.polygon_file:
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name
