import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.direct_impact.measure.impact_measure import ImpactMeasure
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.hazard.measure.hazard_measure import HazardMeasure
from flood_adapt.object_model.interface.strategies import IStrategy, StrategyModel
from flood_adapt.object_model.measure_factory import (
    MeasureFactory,
)


class Strategy(IStrategy):
    """Strategy class that holds all the information for a specific strategy"""

    attrs: StrategyModel
    database_input_path: Union[str, os.PathLike]

    def get_measures(self) -> list[Union[ImpactMeasure, HazardMeasure]]:
        """Gets the measures paths and types"""
        assert self.attrs.measures is not None
        # Get measure paths using a database structure
        measure_paths = [
            Path(self.database_input_path)
            / "measures"
            / measure
            / "{}.toml".format(measure)
            for measure in self.attrs.measures
        ]

        measures = [MeasureFactory.get_measure_object(path) for path in measure_paths]

        return measures

    def get_impact_strategy(self) -> ImpactStrategy:
        return ImpactStrategy(
            [
                measure
                for measure in self.get_measures()
                if issubclass(measure.__class__, ImpactMeasure)
            ]
        )

    def get_hazard_strategy(self) -> HazardStrategy:
        return HazardStrategy(
            [
                measure
                for measure in self.get_measures()
                if issubclass(measure.__class__, HazardMeasure)
            ]
        )

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Create Strategy object from toml file

        Parameters
        ----------
        filepath : Union[str, os.PathLike]
            path to the Strategy's toml file

        Returns
        -------
        IStrategy
            Strategy object
        """
        obj = Strategy()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = StrategyModel.parse_obj(toml)
        # if strategy is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        # TODO does this check need to be here when this is created from a file?
        # We can assume that the file has already passed the test? Much faster!
        obj.get_impact_strategy()  # Need to ensure that the strategy can be created

        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: Union[str, os.PathLike]):
        """_summary_

        Parameters
        ----------
        data : dict[str, Any]
            _description_
        database_input_path : Union[str, os.PathLike]
            _description_

        Returns
        -------
        IStrategy
            _description_
        """
        obj = Strategy()
        obj.attrs = StrategyModel.parse_obj(data)
        obj.database_input_path = database_input_path
        obj.get_impact_strategy()  # Need to ensure that the strategy can be created

        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Strategy to a toml file.

        Parameters
        ----------
        filepath : Union[str, os.PathLike]
            path of the toml file to be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)
