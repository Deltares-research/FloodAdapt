from flood_adapt.objects.measures.measures import (
    HazardMeasure,
    ImpactMeasure,
    Measure,
)
from flood_adapt.objects.object_model import Object


class Strategy(Object):
    """
    Class representing a strategy in FloodAdapt.

    A strategy is a collection of measures that can be applied to a model.

    Attributes
    ----------
    measures : list[str]
        A list of measures associated with the strategy. Should be a list of measure names that are saved in the database.

    """

    measures: list[str]

    _measure_objects: list[Measure] | None = None

    def initialize_measure_objects(self, measures: list[Measure]) -> None:
        """Initialize the measure objects associated with this strategy.

        Parameters
        ----------
        measures : list[Measure]
            A list of measure objects to be associated with this strategy. Should be a list of measure objects that are saved in the database.
        """
        self._measure_objects = measures

    def get_measures(self) -> list[Measure]:
        """Get the measures associated with this strategy.

        Note that this method will return the measure objects, not just their names.
        The measure objects are initialized using the `initialize_measure_objects` method.

        Returns
        -------
        measures : list[Measure]
            The list of measure objects associated with this strategy.

        Raises
        ------
        ValueError
            If the measure objects have not been initialized.
        """
        # Get measure paths using a database structure
        if self._measure_objects is None:
            raise ValueError(
                "Measure objects have not been initialized. Call `initialize_measure_objects()` first."
            )
        return self._measure_objects

    def get_impact_measures(self) -> list[ImpactMeasure]:
        return [
            measure
            for measure in self.get_measures()
            if isinstance(measure, ImpactMeasure)
        ]

    def get_impact_strategy(self) -> "Strategy":
        impact_measures = self.get_impact_measures()
        impact_strategy = Strategy(
            name=self.name,
            measures=[m.name for m in impact_measures],
        )
        impact_strategy.initialize_measure_objects(impact_measures)
        return impact_strategy

    def get_hazard_measures(self) -> list[HazardMeasure]:
        return [
            measure
            for measure in self.get_measures()
            if isinstance(measure, HazardMeasure)
        ]

    def get_hazard_strategy(self) -> "Strategy":
        hazard_measures = self.get_hazard_measures()
        hazard_strategy = Strategy(
            name=self.name,
            measures=[m.name for m in hazard_measures],
        )
        hazard_strategy.initialize_measure_objects(hazard_measures)
        return hazard_strategy
