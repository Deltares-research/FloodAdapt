import os
from abc import ABC
from pathlib import Path
from typing import Any, Union

from flood_adapt.integrator.interface.direct_impacts_adapter_factory import (
    DirectImpactAdapterFactory,
)
from flood_adapt.object_model.interface.measures import ImpactMeasureModel
from flood_adapt.object_model.site import Site


class ImpactMeasure(ABC):
    """ImpactMeasure class that holds all the information for a
    specific measure type that affects the impact model."""

    attrs: ImpactMeasureModel
    database_input_path: Union[str, os.PathLike]

    def get_object_ids(self) -> list[Any]:
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

        Adapter = DirectImpactAdapterFactory.get_adapter(
            site.attrs.direct_impacts.model
        )

        ids = Adapter.get_object_ids(attrs=self.attrs)

        return ids
