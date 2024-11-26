from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from flood_adapt.object_model.interface.scenarios import IScenario


class IOffshoreSfincsHandler(ABC):
    template_path: Path

    @abstractmethod
    def get_resulting_waterlevels(self, scenario: IScenario) -> pd.DataFrame: ...

    @staticmethod
    def requires_offshore_run(scenario: IScenario) -> bool: ...

    @abstractmethod
    def run_offshore(self, scenario: IScenario): ...
