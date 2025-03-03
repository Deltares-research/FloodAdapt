from typing import Any

from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.object_model.interface.scenarios import IScenario, ScenarioModel
from flood_adapt.object_model.utils import finished_file_exists


class Scenario(IScenario):
    """class holding all information related to a scenario."""

    def __init__(self, data: dict[str, Any] | ScenarioModel) -> None:
        """Create a Scenario object."""
        super().__init__(data)

    def load_objects(self, database: IDatabase):
        """Load the event, projection, and strategy objects."""
        self.event = database.events.get(self.attrs.event)
        self.projection = database.projections.get(self.attrs.projection)
        self.strategy = database.strategies.get(self.attrs.strategy)

    def has_run_check(self, database: IDatabase) -> bool:
        """Check if the scenario has been run."""
        results_path = database.scenarios.output_path / self.attrs.name
        return finished_file_exists(results_path)

    def equal_hazard_components(self, other: "IScenario", database: IDatabase) -> bool:
        """Check if two scenarios have the same hazard components."""
        strategy = database.strategies.get(self.attrs.strategy)
        other_strategy = database.strategies.get(other.attrs.strategy)
        equal_hazard_strategy = (
            strategy.get_hazard_strategy() == other_strategy.get_hazard_strategy()
        )

        event = database.events.get(self.attrs.event)
        other_event = database.events.get(other.attrs.event)
        equal_events = event == other_event

        projection = database.projections.get(self.attrs.projection)
        other_projection = database.projections.get(other.attrs.projection)
        equal_projections = (
            projection.get_physical_projection()
            == other_projection.get_physical_projection()
        )

        return equal_hazard_strategy and equal_events and equal_projections

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3
