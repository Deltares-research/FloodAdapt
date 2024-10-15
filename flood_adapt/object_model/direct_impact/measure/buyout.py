import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.interface.measures import BuyoutModel, IBuyout
from flood_adapt.object_model.utils import import_external_file


class Buyout(ImpactMeasure, IBuyout):
    """Subclass of ImpactMeasure describing the measure of buying-out buildings."""

    attrs: BuyoutModel
    database_input_path: Union[str, os.PathLike, None]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IBuyout:
        """Create Buyout from toml file."""
        obj = Buyout()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = BuyoutModel.model_validate(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike, None]
    ) -> IBuyout:
        """Create Buyout from object, e.g. when initialized from GUI."""
        obj = Buyout()
        obj.attrs = BuyoutModel.model_validate(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Buyout to a toml file."""
        if self.attrs.polygon_file:
            new_path = import_external_file(
                self.attrs.polygon_file, Path(filepath).parent
            )
            self.attrs.polygon_file = str(new_path)
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
