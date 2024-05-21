import os
from abc import ABC, abstractmethod
from typing import Union

import pandas as pd


class IBenefit(ABC):
    database_input_path: Union[str, os.PathLike]
    results_path: Union[str, os.PathLike]
    scenarios: pd.DataFrame
    has_run: bool = False

    @abstractmethod
    def check_scenarios(self) -> pd.DataFrame:
        """Check which scenarios are needed for this benefit calculation and if they have already been created"""
        ...
