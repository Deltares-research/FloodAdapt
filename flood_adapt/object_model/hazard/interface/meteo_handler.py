from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import xarray as xr

from flood_adapt.object_model.hazard.interface.models import TimeFrame
from flood_adapt.object_model.interface.config.site import Site


class IMeteoHandler(ABC):
    def __init__(
        self, dir: Optional[Path] = None, site: Optional[Site] = None
    ) -> None: ...

    @abstractmethod
    def download(self, time: TimeFrame): ...

    @abstractmethod
    def read(self, time: TimeFrame) -> xr.Dataset: ...
