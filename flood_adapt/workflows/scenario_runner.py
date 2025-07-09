from flood_adapt import __version__
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.utils import finished_file_exists, write_finished_file
from flood_adapt.objects.scenarios.scenarios import Scenario
from flood_adapt.workflows.hazard_integrator import Hazards
from flood_adapt.workflows.impacts_integrator import Impacts

logger = FloodAdaptLogging.getLogger("ScenarioRunner")


class ScenarioRunner:
    """class holding all information related to a scenario."""

    def __init__(self, database: IDatabase, scenario: Scenario) -> None:
        """Create a Scenario object."""
        self._database = database
        self._load_objects(scenario)
        self.site_info = self._database.site
        self.results_path = self._database.scenarios.output_path / self._scenario.name

    def _load_objects(self, scenario: Scenario) -> None:
        """Load objects from the database."""
        self._scenario = scenario
        self._event = self._database.events.get(scenario.event)
        self._projection = self._database.projections.get(scenario.projection)
        self._strategy = self._database.strategies.get(scenario.strategy)

    def run(self) -> None:
        """Run hazard and impact models for the scenario."""
        self._database.has_run_hazard(self._scenario.name)
        self._load_objects(self._scenario)
        self.results_path.mkdir(parents=True, exist_ok=True)

        # Initiate the logger for all the integrator scripts.
        log_file = self.results_path.joinpath(f"logfile_{self._scenario.name}.log")
        with FloodAdaptLogging.to_file(file_path=log_file):
            logger.info(f"FloodAdapt version `{__version__}`")
            logger.info(f"Started evaluation of `{self._scenario.name}`")
            Hazards(scenario=self._scenario).run()
            Impacts(scenario=self._scenario).run()
            logger.info(f"Finished evaluation of `{self._scenario.name}`")

        # write finished file to indicate that the scenario has been run
        write_finished_file(self.results_path)

    def has_run_check(self):
        """Check if the scenario has been run."""
        return finished_file_exists(self.results_path)
