import os
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.interface.measures import BuyoutModel, IBuyout


class Buyout(ImpactMeasure, IBuyout):
    """Subclass of ImpactMeasure describing the measure of buying-out buildings."""

    attrs: BuyoutModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IBuyout:
        """Create Buyout from toml file."""
        obj = Buyout()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = BuyoutModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[
            str, os.PathLike, None
        ] = None,
    ) -> IBuyout:
        """Create Buyout from object, e.g. when initialized from GUI."""
        if database_input_path is not None:
            FloodAdaptLogging.deprecation_warning(version="0.2.0", reason="`database_input_path` is deprecated. Use the database attribute instead.")
            
        obj = Buyout()
        obj.attrs = BuyoutModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Buyout to a toml file."""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
