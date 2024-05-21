from pathlib import Path
from typing import Any, Optional

from hydromt_fiat.fiat import FiatModel

from flood_adapt.object_model.interface.measures import IImpactMeasure
from flood_adapt.object_model.models.measures import ImpactMeasureModel
from flood_adapt.object_model.object_classes.measure.measure import Measure
from flood_adapt.object_model.site import Site


class ImpactMeasure(Measure, IImpactMeasure):
    """ImpactMeasure class that holds all the information for a
    specific measure type that affects the impact model."""

    _attrs = ImpactMeasureModel

    def get_object_ids(self, fiat_model: Optional[FiatModel] = None) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        # get the site information
        site = Site.load_file(
            Path(self.database_input_path).parent / "static" / "site" / "site.toml"
        )

        # use hydromt-fiat to load the fiat model if it is not provided
        if fiat_model is None:
            fiat_model = FiatModel(
                root=Path(self.database_input_path).parent
                / "static"
                / "templates"
                / "fiat",
                mode="r",
            )
            fiat_model.read()

        # check if polygon file is used, then get the absolute path
        if self._attrs.polygon_file:
            polygon_file = (
                Path(self.database_input_path)
                / "measures"
                / self._attrs.name
                / self._attrs.polygon_file
            )
        else:
            polygon_file = None

        # use the hydromt-fiat method to the ids
        ids = fiat_model.exposure.get_object_ids(
            selection_type=self._attrs.selection_type,
            property_type=self._attrs.property_type,
            non_building_names=site._attrs.fiat.non_building_names,
            aggregation=self._attrs.aggregation_area_type,
            aggregation_area_name=self._attrs.aggregation_area_name,
            polygon_file=polygon_file,
        )

        return ids
