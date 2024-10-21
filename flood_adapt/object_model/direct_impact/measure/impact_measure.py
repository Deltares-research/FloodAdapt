from typing import Any, Optional

from hydromt_fiat.fiat import FiatModel

from flood_adapt.dbs_classes.path_builder import ObjectDir, TopLevelDir, db_path
from flood_adapt.object_model.interface.measures import IMeasure, ImpactMeasureModel
from flood_adapt.object_model.interface.site import Site


class ImpactMeasure(IMeasure[ImpactMeasureModel]):
    """All the information for a specific measure type that affects the impact model."""

    attrs: ImpactMeasureModel

    def get_object_ids(self, fiat_model: Optional[FiatModel] = None) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        # get the site information
        site = Site.load_file(
            db_path(TopLevelDir.static, object_dir=ObjectDir.site) / "site.toml"
        )

        # use hydromt-fiat to load the fiat model if it is not provided
        if fiat_model is None:
            fiat_model = FiatModel(
                root=str(db_path(TopLevelDir.static) / "templates" / "fiat"),
                mode="r",
            )
            fiat_model.read()

        # check if polygon file is used, then get the absolute path
        if self.attrs.polygon_file:
            polygon_file = (
                db_path(TopLevelDir.input, ObjectDir.measure, self.attrs.name)
                / self.attrs.polygon_file
            )
        else:
            polygon_file = None

        # use the hydromt-fiat method to the ids
        ids = fiat_model.exposure.get_object_ids(
            selection_type=self.attrs.selection_type,
            property_type=self.attrs.property_type,
            non_building_names=site.attrs.fiat.non_building_names,
            aggregation=self.attrs.aggregation_area_type,
            aggregation_area_name=self.attrs.aggregation_area_name,
            polygon_file=polygon_file,
        )

        del fiat_model
        return ids
