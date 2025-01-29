from typing import Any

from flood_adapt import __version__
from flood_adapt.adapter.impacts_integrator import Impacts
from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.interface.scenarios import IScenario, ScenarioModel
from flood_adapt.object_model.utils import finished_file_exists, write_finished_file


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
        self.impacts = Impacts(scenario=self, database=database)

    def run(self, database: IDatabase):
        """Run hazard and impact models for the scenario."""
        self.load_objects(database)

        results_path = database.scenarios.output_path / self.attrs.name
        log_file = results_path.joinpath(f"logfile_{self.attrs.name}.log")

        # Initiate the logger for all the integrator scripts.
        with FloodAdaptLogging.to_file(file_path=log_file):
            self.logger.info(f"FloodAdapt version `{__version__}`")
            self.logger.info(f"Started evaluation of `{self.attrs.name}`")

            hazard_models: list[IHazardAdapter] = [
                database.static.get_overland_sfincs_model(),
            ]
            for hazard in hazard_models:
                if not hazard.has_run(self):
                    hazard.run(scenario=self, database=database)
                else:
                    self.logger.info(
                        f"Hazard for scenario '{self.attrs.name}' has already been run."
                    )

            impact_models: list[IImpactAdapter] = [
                database.static.get_fiat_model(),
            ]
            for impact in impact_models:
                if not impact.has_run(self):
                    impact.run(scenario=self, database=database)
                else:
                    self.logger.info(
                        f"Impacts for scenario '{self.attrs.name}' has already been run."
                    )

            self.logger.info(f"Finished evaluation of `{self.attrs.name}`")

        # write finished file to indicate that the scenario has been run
        write_finished_file(results_path)

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
