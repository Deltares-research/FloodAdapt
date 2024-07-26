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
    """Strategy class that holds all the information for a specific strategy."""

    attrs: StrategyModel

    def get_measures(self) -> list[Union[ImpactMeasure, HazardMeasure]]:
        """Get the measures paths and types."""
        assert self.attrs.measures is not None
        # Get measure paths using a database structure
        measure_paths = [
            Path(self.database.input_path)
            / "measures"
            / measure
            / "{}.toml".format(measure)
            for measure in self.attrs.measures
        ]

        measures = [MeasureFactory.get_measure_object(path) for path in measure_paths]

        return measures

    def get_impact_strategy(self, validate=False) -> ImpactStrategy:
        return ImpactStrategy(
            [
                measure
                for measure in self.get_measures()
                if issubclass(measure.__class__, ImpactMeasure)
            ],
            validate=validate,
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
    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """Create Strategy object from toml file.

        Parameters
        ----------
        filepath : Union[str, os.PathLike]
            path to the Strategy's toml file
        validate : bool, optional
            if this is true the affected buildings from the impact-measures
            will be checked to ensure they do not overlap, by default False

        Returns
        -------
        IStrategy
            Strategy object
        """
        obj = Strategy()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = StrategyModel.model_validate(toml)
        # Need to ensure that the strategy can be created
        if validate:
            obj.get_impact_strategy(validate=True)

        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[
            str, os.PathLike
        ] = None,  # TODO deprecate database_input_path
        validate: bool = True,
    ):
        """_summary_.

        Parameters
        ----------
        data : dict[str, Any]
            dictionary with the data
        database_input_path : Union[str, os.PathLike]
            path like object pointing to the location of the input files
        validate : bool, optional
            if this is true the affected buildings from the impact-measures
            will be checked to ensure they do not overlap, by default True

        Returns
        -------
        IStrategy
            _description_
        """
        obj = Strategy()
        obj.attrs = StrategyModel.model_validate(data)
        # Need to ensure that the strategy can be created
        if validate:
            obj.get_impact_strategy(validate=True)

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
