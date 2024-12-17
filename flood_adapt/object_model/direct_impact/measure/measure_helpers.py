from typing import Any, Optional

from hydromt_fiat.fiat import FiatModel

from flood_adapt.object_model.interface.measures import IMeasure, MeasureType
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.site import Site


def get_object_ids(
    measure: IMeasure, fiat_model: Optional[FiatModel] = None
) -> list[Any]:
    """Get ids of objects that are affected by the measure.

    Returns
    -------
    list[Any]
        list of ids
    """
    if not MeasureType.is_impact(measure.attrs.type):
        raise ValueError(
            f"Measure type {measure.attrs.type} is not an impact measure. "
            "Can only retrieve object ids for impact measures."
        )

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
    if measure.attrs.polygon_file:
        polygon_file = (
            db_path(TopLevelDir.input, ObjectDir.measure, measure.attrs.name)
            / measure.attrs.polygon_file
        )
    else:
        polygon_file = None

    # use the hydromt-fiat method to the ids
    ids = fiat_model.exposure.get_object_ids(
        selection_type=measure.attrs.selection_type,
        property_type=measure.attrs.property_type,
        non_building_names=site.attrs.fiat.non_building_names,
        aggregation=measure.attrs.aggregation_area_type,
        aggregation_area_name=measure.attrs.aggregation_area_name,
        polygon_file=polygon_file,
    )

    return ids
