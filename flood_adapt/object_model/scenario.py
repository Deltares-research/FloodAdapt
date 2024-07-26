import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt import __version__
from flood_adapt.integrator.sfincs_adapter import SfincsAdapter
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.interface.scenarios import IScenario, ScenarioModel


class Scenario(IScenario):
    """class holding all information related to a scenario."""

    attrs: ScenarioModel
    direct_impacts: DirectImpacts

    @property
    def results_path(self) -> Path:
        return self.database.scenarios.get_database_path(get_input_path=False).joinpath(
            self.attrs.name
        )

    @property
    def site_info(self):
        return self.database.site

    def __init__(self) -> None:
        self._logger = FloodAdaptLogging.getLogger(__name__)

    def init_object_model(self) -> "Scenario":
        """Create a Direct Impact object."""
        self.direct_impacts = DirectImpacts(
            scenario=self.attrs,
            results_path=self.results_path,
        )
        return self

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Create Scenario from toml file."""
        obj = Scenario()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ScenarioModel.model_validate(toml)
        return obj

    @staticmethod
    def load_dict(
        data: dict[str, Any], database_input_path: os.PathLike = None
    ):  # TODO deprecate database_input_path
        """Create Scenario from object, e.g. when initialized from GUI."""
        obj = Scenario()
        obj.attrs = ScenarioModel.model_validate(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Save Scenario to a toml file."""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    def run(self):
        """Run direct impact models for the scenario."""
        self.init_object_model()
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
                template_path = Path(
                    self.database.static_path / "templates" / "overland"
                )
                with SfincsAdapter(model_root=template_path) as sfincs_adapter:
                    sfincs_adapter.run(self)
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

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3
