from abc import ABC
from typing import Any


class ImpactMeasure(ABC):
    """All the information for a specific measure type that affects the impact model."""

    def get_object_ids(self) -> list[Any]:
        """Get ids of objects that are affected by the measure.

        Returns
        -------
        list[Any]
            list of ids
        """
        adapter = self.database.static.get_fiat_model()

        ids = adapter.get_measure_building_ids(self)

        return ids
