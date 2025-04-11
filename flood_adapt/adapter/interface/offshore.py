from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from flood_adapt.objects.scenarios.scenarios import Scenario


class IOffshoreSfincsHandler(ABC):
    template_path: Path

    @abstractmethod
    def get_resulting_waterlevels(self, scenario: Scenario) -> pd.DataFrame: ...

    @staticmethod
    def requires_offshore_run(scenario: Scenario) -> bool: ...

    @abstractmethod
    def run_offshore(self, scenario: Scenario): ...
