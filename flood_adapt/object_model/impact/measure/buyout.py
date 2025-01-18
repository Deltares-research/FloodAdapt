import os
from pathlib import Path

from flood_adapt.object_model.impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.interface.measures import BuyoutModel, IMeasure
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class Buyout(IMeasure[BuyoutModel], ImpactMeasure):
    """Subclass of ImpactMeasure describing the measure of buying-out buildings."""

    _attrs_type = BuyoutModel

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save the additional files to the database."""
        if self.attrs.polygon_file:
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.polygon_file
            )
            path = save_file_to_database(src_path, Path(output_dir))
            # Update the shapefile path in the object so it is saved in the toml file as well
            self.attrs.polygon_file = path.name
