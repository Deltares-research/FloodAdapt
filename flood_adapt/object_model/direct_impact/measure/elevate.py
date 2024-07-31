import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.interface.measures import ElevateModel, IElevate


class Elevate(ImpactMeasure, IElevate):
    """Subclass of ImpactMeasure describing the measure of elevating buildings by a specific height."""

    attrs: ElevateModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IElevate:
        """Create Elevate from toml file."""
        obj = Elevate()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ElevateModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike, None] = None,
    ) -> IElevate:
        """Create Elevate from object, e.g. when initialized from GUI."""
        if database_input_path is not None:
            FloodAdaptLogging.deprecation_warning(
                version="0.2.0",
                reason="`database_input_path` is deprecated. Use the database attribute instead.",
            )
        obj = Elevate()
        obj.attrs = ElevateModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Elevate to a toml file."""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
