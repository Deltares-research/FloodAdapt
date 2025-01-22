from typing import Any

from flood_adapt import __version__
from flood_adapt.adapter.direct_impacts_integrator import Impacts
from flood_adapt.adapter.interface.hazard_adapter import IHazardAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.interface.events import IEvent
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.projections import IProjection
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.strategies import IStrategy
from flood_adapt.object_model.utils import finished_file_exists, write_finished_file


class Scenario(IScenario, DatabaseUser):
    """class holding all information related to a scenario."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Create a Scenario object."""
        super().__init__(data)
        self.site_info = self.database.site
        self.results_path = self.database.scenarios.output_path / self.attrs.name

    @property
    def event(self) -> IEvent:
        if not hasattr(self, "_event"):
            self._event = self.database.events.get(self.attrs.event)
        return self._event

    @property
    def projection(self) -> IProjection:
        if not hasattr(self, "_projection"):
            self._projection = self.database.projections.get(self.attrs.projection)
        return self._projection

    @property
    def strategy(self) -> IStrategy:
        if not hasattr(self, "_strategy"):
            self._strategy = self.database.strategies.get(self.attrs.strategy)
        return self._strategy

    @property
    def impacts(self) -> Impacts:
        return Impacts(
            scenario=self,
        )

    def run(self):
        """Run hazard and impact models for the scenario."""
        self.results_path.mkdir(parents=True, exist_ok=True)

        # Initiate the logger for all the integrator scripts.
        log_file = self.results_path.joinpath(f"logfile_{self.attrs.name}.log")
        with FloodAdaptLogging.to_file(file_path=log_file):
            self.logger.info(f"FloodAdapt version {__version__}")
            self.logger.info(
                f"Started evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )

            hazard_models: list[IHazardAdapter] = [
                self.database.static.get_overland_sfincs_model(),
            ]
            for hazard in hazard_models:
                if not hazard.has_run(self):
                    hazard.run(self)
                else:
                    self.logger.info(
                        f"Hazard for scenario '{self.attrs.name}' has already been run."
                    )

            if not self.impacts.has_run:
                self.impacts.run()
            else:
                self.logger.info(
                    f"Impacts for scenario '{self.attrs.name}' has already been run."
                )

            self.logger.info(
                f"Finished evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )

        # write finished file to indicate that the scenario has been run
        write_finished_file(self.results_path)

    def has_run_check(self):
        """Check if the scenario has been run."""
        return finished_file_exists(self.results_path)

    def equal_hazard_components(self, other: "IScenario") -> bool:
        """Check if two scenarios have the same hazard components."""
        equal_hazard_strategy = (
            self.strategy.get_hazard_strategy() == other.strategy.get_hazard_strategy()
        )
        equal_events = self.attrs.event == other.attrs.event
        equal_projections = (
            self.projection.get_physical_projection()
            == other.projection.get_physical_projection()
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
