from flood_adapt import __version__
from flood_adapt.dbs_classes.interface.database import IDatabase
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.utils import finished_file_exists, write_finished_file
from flood_adapt.objects.scenarios.scenarios import Scenario

logger = FloodAdaptLogging.getLogger("ScenarioRunner")


class ScenarioRunner:
    """class holding all information related to a scenario."""

    def __init__(self, database: IDatabase, scenario: Scenario) -> None:
        """Create a Scenario object."""
        self._database = database
        self._scenario = scenario
        self.site_info = self._database.site
        self.results_path = self._database.scenarios.output_path / self._scenario.name

        self._event = None
        self._projection = None
        self._strategy = None

        self._hazard_models = None
        self._impact_models = None

    @property
    def impact_models(self):
        """Return the list of impact models."""
        if self._impact_models is not None:
            return self._impact_models
        self._impact_models = self._database.static.get_impact_models()
        return self._impact_models

    @property
    def hazard_models(self):
        """Return the list of hazard models."""
        if self._hazard_models is not None:
            return self._hazard_models
        self._hazard_models = self._database.static.get_hazard_models()
        return self._hazard_models

    def _load_objects(self, scenario: Scenario) -> None:
        """Load objects from the database."""
        self._scenario = scenario
        self._event = self._database.events.get(scenario.event)
        self._projection = self._database.projections.get(scenario.projection)
        self._strategy = self._database.strategies.get(scenario.strategy)

    ### General methods ###
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
            self._run_hazards()
            self._run_impacts()
            self._run_postprocessing_hooks()
            logger.info(f"Finished evaluation of `{self._scenario.name}`")

        # write finished file to indicate that the scenario has been run
        write_finished_file(self.results_path)

    def has_run_check(self):
        """Check if the scenario has been run."""
        return finished_file_exists(self.results_path)

    ### Hazard methods ###
    def _run_hazards(self) -> None:
        """Run the hazard model for the scenario."""
        if self.hazard_run_check():
            logger.info(f"Hazards for {self._scenario.name} have already been run.")
            return
        for model in self.hazard_models:
            model.run(self._scenario)

    def hazard_run_check(self) -> bool:
        """Check if the impact has been run.

        Returns
        -------
        bool
            _description_
        """
        return all(model.has_run(self._scenario) for model in self.hazard_models)

    ### Impact methods ###
    def _run_impacts(self) -> None:
        """Run the impact model(s)."""
        if self.impacts_run_check():
            logger.info(f"Impacts for {self._scenario.name} have already been run.")
            return
        for model in self.impact_models:
            model.run(self._scenario)

    def impacts_run_check(self) -> bool:
        """Check if the impact has been run.

        Returns
        -------
        bool
            _description_
        """
        return all(model.has_run(self._scenario) for model in self.impact_models)

    def _run_postprocessing_hooks(self) -> None:
        """Run the post-processing hook if configured."""
        hooks = self._database.get_postprocessing_hooks()
        if hooks is None:
            return

        for name, hook in hooks.items():
            logger.info(f"Running post-processing hook {name}...")
            try:
                hook(self._database, self._scenario, self.results_path)
            except Exception as e:
                logger.error(f"Post-processing hook failed: {e}")
                if self._database.config.ignore_postprocess_errors:
                    logger.warning("Continuing despite post-processing hook error.")
                else:
                    raise
