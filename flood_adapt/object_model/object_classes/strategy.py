from typing import Any, Union

from flood_adapt.dbs_classes.dbs_measure import DbsMeasure
from flood_adapt.object_model.direct_impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.hazard.hazard_strategy import HazardStrategy
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.models.strategies import StrategyModel
from flood_adapt.object_model.object_classes.flood_adapt_object import FAObject
from flood_adapt.object_model.object_classes.measure.hazard_measure.hazard_measure import (
    HazardMeasure,
)
from flood_adapt.object_model.object_classes.measure.impact_measure.impact_measure import (
    ImpactMeasure,
)


class Strategy(FAObject, IStrategy):
    """Strategy class that holds all the information for a specific strategy"""

    _attrs = StrategyModel
    _type = "Strategies"

    def get_measures(self) -> list[Union[ImpactMeasure, HazardMeasure]]:
        """Gets the measures paths and types

        Returns
        -------
        list[Union[ImpactMeasure, HazardMeasure]]
            List of measures

        Raises
        ------
        ValueError
            If the 'measures' attribute is None
        """
        if self.attrs.measures is None:
            raise ValueError("The 'measures' attribute cannot be None.")

        # Get measure paths using a database structure
        measures = [DbsMeasure.get(measure) for measure in self.attrs.measures]

        return measures

    def get_impact_strategy(self, validate=False) -> ImpactStrategy:
        """Get the impact strategy

        Parameters
        ----------
        validate : bool, optional
            if this is true the affected buildings from the impact-measures
            will be checked to ensure they do not overlap, by default False

        Returns
        -------
        ImpactStrategy
            The impact strategy
        """
        return ImpactStrategy(
            [
                measure
                for measure in self.get_measures()
                if isinstance(measure, ImpactMeasure)
            ],
            validate=validate,
        )

    def get_hazard_strategy(self) -> HazardStrategy:
        """Get the hazard strategy

        Returns
        -------
        HazardStrategy
            The hazard strategy
        """
        return HazardStrategy(
            [
                measure
                for measure in self.get_measures()
                if isinstance(measure, HazardMeasure)
            ]
        )

    @classmethod
    def load_dict(
        cls,
        data: dict[str, Any],
        validate: bool = True,
    ):
        """Get a Strategy object from a dict containing the object's attributes

        Parameters
        ----------
        data : dict[str, Any]
            dictionary with the data
        validate : bool, optional
            if this is true the affected buildings from the impact-measures
            will be checked to ensure they do not overlap, by default True

        Returns
        -------
        IStrategy
            _description_
        """
        obj = super().load_dict(cls, data)
        # The impact strategy has a seperate validation method
        if validate:
            obj.get_impact_strategy(validate=True)

        return obj
