import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.hazard.measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.interface.measures import (
    IPump,
    PumpModel,
)


class Pump(HazardMeasure, IPump):
    """Subclass of HazardMeasure describing the measure of building a floodwall with a specific height."""

    attrs: PumpModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IPump:
        """Create Floodwall from toml file."""
        obj = Pump()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = PumpModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[
            str, os.PathLike, None
        ] = None,
    ) -> IPump:
        """Create Floodwall from object, e.g. when initialized from GUI."""
        if database_input_path is not None:
            FloodAdaptLogging.deprecation_warning(version="0.2.0", reason="`database_input_path` is deprecated. Use the database attribute instead.")
        obj = Pump()
        obj.attrs = PumpModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Floodwall to a toml file."""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
