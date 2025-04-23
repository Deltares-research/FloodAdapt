from pathlib import Path

from flood_adapt.misc.database_user import DatabaseUser
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.objects.projections.projections import SocioEconomicChange
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.objects.strategies.strategies import Strategy
from flood_adapt.workflows.floodmap import FloodMap


class Impacts(DatabaseUser):
    """All information related to the impacts of the scenario.

    Includes methods to run the impact models or check if they has already been run.
    """

    logger = FloodAdaptLogging.getLogger("Impacts")
    name: str

    def __init__(self, scenario: Scenario):
        self.name = scenario.name
        self.scenario = scenario
        self.site_info = self.database.site
        self.models = [
            self.database.static.get_fiat_model()
        ]  # for now only FIAT adapter

    @property
    def hazard(self) -> FloodMap:
        return FloodMap(self.name)

    @property
    def socio_economic_change(self) -> SocioEconomicChange:
        return self.database.projections.get(
            self.scenario.projection
        ).socio_economic_change

    @property
    def impact_strategy(self) -> Strategy:
        return self.database.strategies.get(
            self.scenario.strategy
        ).get_impact_strategy()

    @property
    def results_path(self) -> Path:
        return db_path(
            TopLevelDir.output, object_dir=ObjectDir.scenario, obj_name=self.name
        )

    @property
    def impacts_path(self) -> Path:
        return self.results_path / "Impacts"

    @property
    def has_run(self) -> bool:
        return self.has_run_check()

    def run(self):
        """Run the impact model(s)."""
        if self.has_run:
            self.logger.info("Impacts have already been run.")
            return
        for model in self.models:
            model.run(self.scenario)

    def has_run_check(self) -> bool:
        """Check if the impact has been run.

        Returns
        -------
        bool
            _description_
        """
        checks = []
        for model in self.models:
            checks.append(model.has_run(self.scenario))
        return all(checks)
