from pathlib import Path

from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.database_user import DatabaseUser
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.projections import SocioEconomicChange
from flood_adapt.object_model.interface.scenarios import IScenario


class Impacts(DatabaseUser):
    """All information related to the impacts of the scenario.

    Includes methods to run the impact model or check if it has already been run.
    """

    logger = FloodAdaptLogging.getLogger(__name__)
    name: str
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy

    def __init__(self, scenario: IScenario):
        self.name = scenario.attrs.name
        self.scenario = scenario
        self.site_info = self.database.site
        self.models: list[IImpactAdapter] = [self.database.static.get_fiat_model()]

        self.set_socio_economic_change(scenario.attrs.projection)
        self.set_impact_strategy(scenario.attrs.strategy)

    @property
    def hazard(self) -> FloodMap:
        return FloodMap(self.name)

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

    def set_socio_economic_change(self, projection: str) -> None:
        """Set the SocioEconomicChange object of the scenario.

        Parameters
        ----------
        projection : str
            Name of the projection used in the scenario
        """
        self.socio_economic_change = self.database.projections.get(
            projection
        ).get_socio_economic_change()

    def set_impact_strategy(self, strategy: str) -> None:
        """Set the ImpactStrategy object of the scenario.

        Parameters
        ----------
        strategy : str
            Name of the strategy used in the scenario
        """
        self.impact_strategy = self.database.strategies.get(
            strategy
        ).get_impact_strategy()
