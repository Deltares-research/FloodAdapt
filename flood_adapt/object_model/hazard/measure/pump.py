import os
from pathlib import Path
from typing import Any

from flood_adapt.object_model.interface.measures import (
    IPump,
    PumpModel,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class Pump(IPump):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height."""

    attrs: PumpModel

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, PumpModel):
            self.attrs = data
        else:
            self.attrs = PumpModel.model_validate(data)

    def save_additional(self, toml_path: Path | str | os.PathLike) -> None:
        if self.attrs.polygon_file:
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name
