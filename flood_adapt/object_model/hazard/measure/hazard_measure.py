import os
from abc import ABC
from typing import Union

from flood_adapt.object_model.interface.measures import HazardMeasureModel


class HazardMeasure(ABC):
    """HazardMeasure class that holds all the information for a specific measure type that affects the impact model"""

    attrs: HazardMeasureModel
    database_input_path: Union[str, os.PathLike]
