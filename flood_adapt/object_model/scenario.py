import os
from typing import Any

from flood_adapt import __version__
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.hazard import ScenarioModel
from flood_adapt.object_model.interface.database import ObjectDir, TopLevelDir, db_path
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.utils import finished_file_exists, write_finished_file


class Scenario(IScenario):
    """class holding all information related to a scenario."""

    attrs: ScenarioModel
    direct_impacts: DirectImpacts

    def __init__(self, data: dict[str, Any]) -> None:
        """Create a Direct Impact object."""
        self._logger = FloodAdaptLogging.getLogger(__name__)

        if isinstance(data, ScenarioModel):
            self.attrs = data
        else:
            self.attrs = ScenarioModel.model_validate(data)

        self.site_info = Site.load_file(
            db_path(TopLevelDir.static, ObjectDir.site) / "site.toml"
        )
        self.results_path = db_path(TopLevelDir.output, self.dir_name, self.attrs.name)
        self.direct_impacts = DirectImpacts(
            scenario=self.attrs,
            results_path=self.results_path,
        )

    def run(self):
        """Run direct impact models for the scenario."""
        # self.init_object_model()
        os.makedirs(self.results_path, exist_ok=True)

        # Initiate the logger for all the integrator scripts.
        log_file = self.results_path.joinpath(f"logfile_{self.attrs.name}.log")
        with FloodAdaptLogging.to_file(file_path=log_file):
            self._logger.info(f"FloodAdapt version {__version__}")
            self._logger.info(
                f"Started evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )
            # preprocess model input data first, then run, then post-process
            if not self.direct_impacts.hazard.has_run:
                self.direct_impacts.hazard.preprocess_models()
                self.direct_impacts.hazard.run_models()
                self.direct_impacts.hazard.postprocess_models()
            else:
                print(f"Hazard for scenario '{self.attrs.name}' has already been run.")
            if not self.direct_impacts.has_run:
                self.direct_impacts.preprocess_models()
                self.direct_impacts.run_models()
                self.direct_impacts.postprocess_models()
            else:
                print(
                    f"Direct impacts for scenario '{self.attrs.name}' has already been run."
                )
            self._logger.info(
                f"Finished evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )

        # write finished file to indicate that the scenario has been run
        write_finished_file(self.results_path)

    def has_run_check(self):
        """Check if the scenario has been run."""
        return finished_file_exists(self.results_path)
