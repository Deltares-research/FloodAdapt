import os
from typing import Any

from flood_adapt import __version__
from flood_adapt.integrator.direct_impacts_integrator import DirectImpacts
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.misc.log import FloodAdaptLogging
from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.scenarios import IScenario, ScenarioModel
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.projection import Projection
from flood_adapt.object_model.strategy import Strategy
from flood_adapt.object_model.utils import finished_file_exists, write_finished_file


class Scenario(IScenario):
    """class holding all information related to a scenario."""

    attrs: ScenarioModel

    direct_impacts: DirectImpacts

    def __init__(self, data: dict[str, Any]) -> None:
        """Create a Direct Impact object."""
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
        )

    def run(self):
        """Run direct impact models for the scenario."""
        os.makedirs(self.results_path, exist_ok=True)

        # Initiate the logger for all the integrator scripts.
        log_file = self.results_path.joinpath(f"logfile_{self.attrs.name}.log")
        with FloodAdaptLogging.to_file(file_path=log_file):
            self.logger.info(f"FloodAdapt version {__version__}")
            self.logger.info(
                f"Started evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )

            # preprocess model input data first, then run, then post-process
            if not self.direct_impacts.hazard.has_run:
                template_path = db_path(TopLevelDir.static) / "templates" / "overland"
                with SfincsAdapter(model_root=template_path) as sfincs_adapter:
                    sfincs_adapter.run(self)
            else:
                self.logger.info(
                    f"Hazard for scenario '{self.attrs.name}' has already been run."
                )

            if not self.direct_impacts.has_run:
                self.direct_impacts.preprocess_models()
                self.direct_impacts.run_models()
                self.direct_impacts.postprocess_models()
            else:
                self.logger.info(
                    f"Direct impacts for scenario '{self.attrs.name}' has already been run."
                )

            self.logger.info(
                f"Finished evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
            )

        # write finished file to indicate that the scenario has been run
        write_finished_file(self.results_path)

    def has_run_check(self):
        """Check if the scenario has been run."""
        return finished_file_exists(self.results_path)

    def equal_hazard_components(self, scenario: "IScenario") -> bool:
        """Check if two scenarios have the same hazard components."""

        def equal_hazard_strategy():
            lhs = Strategy.load_file(
                db_path(object_dir=ObjectDir.strategy, obj_name=self.attrs.strategy)
                / f"{self.attrs.strategy}.toml"
            ).get_hazard_strategy()
            rhs = Strategy.load_file(
                db_path(object_dir=ObjectDir.strategy, obj_name=scenario.attrs.strategy)
                / f"{scenario.attrs.strategy}.toml"
            ).get_hazard_strategy()
            return lhs == rhs

        def equal_events():
            return self.attrs.event == scenario.attrs.event

        def equal_projections():
            lhs = Projection.load_file(
                db_path(object_dir=ObjectDir.projection, obj_name=self.attrs.projection)
                / f"{self.attrs.projection}.toml"
            ).get_physical_projection()
            rhs = Projection.load_file(
                db_path(
                    object_dir=ObjectDir.projection, obj_name=scenario.attrs.projection
                )
                / f"{scenario.attrs.projection}.toml"
            ).get_physical_projection()
            return lhs == rhs

        return equal_hazard_strategy() & equal_events() & equal_projections()

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3
