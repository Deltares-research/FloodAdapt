from abc import ABC, abstractmethod
from pathlib import Path

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.site import Site


class IScenario(ABC):
    """Scenario class that holds all the information for a specific scenario"""

    _site_info: Site
    _direct_impacts: DirectImpacts
    _results_path: Path

    @property
    @abstractmethod
    def site_info(self) -> Site: ...

    @property
    @abstractmethod
    def direct_impacts(self) -> DirectImpacts: ...

    @property
    @abstractmethod
    def results_path(self) -> Path: ...

    @abstractmethod
    def run(self) -> None: ...
