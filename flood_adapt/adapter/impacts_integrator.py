from pathlib import Path

from flood_adapt.adapter.interface.impact_adapter import IImpactAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.hazard.floodmap import FloodMap
from flood_adapt.object_model.impact.impact_strategy import ImpactStrategy
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.projections import SocioEconomicChange
from flood_adapt.object_model.interface.scenarios import IScenario


class Impacts:
    """All information related to the impacts of the scenario.

    Includes methods to run the impact models or check if they has already been run.
    """

    logger = FloodAdaptLogging.getLogger("Impacts")
    name: str
    socio_economic_change: SocioEconomicChange
    impact_strategy: ImpactStrategy

    def __init__(
        self,
        scenario: IScenario,
        flood_map: FloodMap,
        impact_models: list[IImpactAdapter],
        site_info: Site,
        output_path: Path,
    ):
        self.name = scenario.attrs.name
        self.scenario = scenario
        self.flood_map = flood_map
        self.site_info = site_info
        self.models: list[IImpactAdapter] = impact_models
        self.results_path = output_path
        self.impacts_path = self.results_path / "Impacts"

        self.impact_strategy = self.scenario.strategy.get_impact_strategy()
        self.socio_economic_change = (
            self.scenario.projection.get_socio_economic_change()
        )

    def run(self, database):
        """Run the impact model(s)."""
        if self.has_run_check(database):
            self.logger.info("Impacts have already been run.")
            return
        for model in self.models:
            model.run(self.scenario, database)

    def has_run_check(self, database) -> bool:
        """Check if the impact has been run.

        Returns
        -------
        bool
            _description_
        """
        checks = []
        for model in self.models:
            checks.append(model.has_run(self.scenario, database))
        return all(checks)
