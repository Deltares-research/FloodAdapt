import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.measure.impact_measure import (
    ImpactMeasure,
)
from flood_adapt.object_model.interface.measures import FloodProofModel, IFloodProof


class FloodProof(ImpactMeasure, IFloodProof):
    """Subclass of ImpactMeasure describing the measure of flood-proof buildings."""

    attrs: FloodProofModel
    database_input_path: Union[str, os.PathLike, None]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> IFloodProof:
        """Create FloodProof from toml file."""
        obj = FloodProof()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = FloodProofModel.parse_obj(toml)
        # if measure is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: Union[str, os.PathLike, None]
    ) -> IFloodProof:
        """Create FloodProof from object, e.g. when initialized from GUI."""
        obj = FloodProof()
        obj.attrs = FloodProofModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save FloodProof to a toml file."""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
