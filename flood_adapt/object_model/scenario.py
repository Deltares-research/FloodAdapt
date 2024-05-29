import gc
import logging
import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.hazard.hazard import ScenarioModel
from flood_adapt.object_model.interface.scenarios import IScenario


class Scenario(IScenario):
    """class holding all information related to a scenario."""

    attrs: ScenarioModel
    direct_impacts: DirectImpacts
    database_input_path: Union[str, os.PathLike]

    def init_object_model(self) -> "Scenario":
        """Create a Direct Impact object"""
        from flood_adapt.dbs_controller import (
            Database,  # TODO: Fix circular import and move to top of file. There is too much entanglement between classes to fix this now
        )

        database = Database()
        self.site_info = database.site
        self.results_path = database.output_path.joinpath("Scenarios", self.attrs.name
        )
        self.direct_impacts = DirectImpacts(
            scenario=self.attrs,
            database=database,
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
        # if scenario is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: os.PathLike):
        """Create Scenario from object, e.g. when initialized from GUI."""
        obj = Scenario()
        obj.attrs = ScenarioModel.model_validate(data)
        obj.database_input_path = database_input_path
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
        self.initiate_root_logger(
            self.results_path.joinpath(f"logfile_{self.attrs.name}.log")
        )
        version = "0.1.0"
        logging.info(f"FloodAdapt version {version}")
        logging.info(
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

        logging.info(
            f"Finished evaluation of {self.attrs.name} for {self.site_info.attrs.name}"
        )
        self.close_root_logger_handlers()

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3

    @staticmethod
    def initiate_root_logger(filename):
        # Create a root logger and set the minimum logging level.
        logging.getLogger("").setLevel(logging.INFO)

        # Create a file handler and set the required logging level.
        fh = logging.FileHandler(filename=filename, mode="w")
        fh.setLevel(logging.DEBUG)

        # Create a console handler and set the required logging level.
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)  # Can be also set to WARNING

        # Create a formatter and add to the file and console handlers.
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %I:%M:%S %p",
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Add the file and console handlers to the root logger.
        logging.getLogger("").addHandler(fh)
        logging.getLogger("").addHandler(ch)

    @staticmethod
    def close_root_logger_handlers():
        """Close and remove all handlers from the root logger.

        This way, it is possible to delete the log file, which is not possible if
        the file is still open.
        """
        # Get the root logger
        root_logger = logging.getLogger("")

        # Retrieve the handlers
        handlers = root_logger.handlers

        # Close and remove the handlers
        for handler in handlers:
            handler.close()
            root_logger.removeHandler(handler)

        # Use garbage collector to ensure file handles are properly cleaned up
        gc.collect()
        logging.shutdown()
