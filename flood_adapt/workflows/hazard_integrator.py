from pathlib import Path

from flood_adapt.misc.database_user import DatabaseUser
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.misc.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.objects.scenarios.scenarios import Scenario

logger = FloodAdaptLogging.getLogger("Hazards")


class Hazards(DatabaseUser):
    """All information related to the Hazards of the scenario.

    Includes methods to run the hazard models or check if they has already been run.
    """

    name: str

    def __init__(self, scenario: Scenario):
        self.name = scenario.name
        self.scenario = scenario
        self.site_info = self.database.site

    @property
    def models(self):
        """Return the list of impact models."""
        return self.database.static.get_hazard_models()

    @property
    def results_path(self) -> Path:
        return db_path(
            TopLevelDir.output, object_dir=ObjectDir.scenario, obj_name=self.name
        )

    @property
    def has_run(self) -> bool:
        return self.has_run_check()

    def run(self):
        """Run the impact model(s)."""
        if self.has_run:
            logger.info(f"Hazards for {self.scenario.name} have already been run.")
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
