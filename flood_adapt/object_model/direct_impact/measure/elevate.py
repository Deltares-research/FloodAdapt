import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.interface.measures import ElevateModel, IElevate
from flood_adapt.object_model.utils import import_external_file


class Elevate(ImpactMeasure, IElevate):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height."""

    attrs: ElevateModel
    database_input_path: Union[str, os.PathLike, None]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IElevate:
        """Create Elevate from toml file."""
        obj = Elevate()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ElevateModel.model_validate(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike, None]
    ) -> IElevate:
        """Create Elevate from object, e.g. when initialized from GUI."""
        obj = Elevate()
        obj.attrs = ElevateModel.model_validate(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike], additional_files: bool = False):
        """Save Elevate to a toml file."""
        if additional_files:
            if self.attrs.polygon_file:
                new_path = import_external_file(
                    self.attrs.polygon_file, Path(filepath).parent
                )
                self.attrs.polygon_file = str(new_path)

        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
