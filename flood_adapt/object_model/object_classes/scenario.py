import gc
import logging
import os
from pathlib import Path

from flood_adapt.object_model.direct_impacts import DirectImpacts
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.models.scenarios import ScenarioModel
from flood_adapt.object_model.object_classes.flood_adapt_object import FAObject
from flood_adapt.object_model.site import Site


class Scenario(FAObject, IScenario):
    """Scenario class that holds all the information for a specific scenario"""

    _attrs = ScenarioModel
    _type = "Scenarios"
    _site_info = Site
    _direct_impacts = DirectImpacts
    _results_path = Path

    @property
    def site_info(self) -> Site:
        """Get the site information of the scenario

        Returns
        -------
        Site
            The site information of the scenario
        """
        return self._site_info
    
    @property
    def direct_impacts(self) -> DirectImpacts:
        """Get the direct impacts of the scenario

        Returns
        -------
        DirectImpacts
            The direct impacts of the scenario
        """
        return self._direct_impacts
    
    @property
    def results_path(self) -> Path:
        """Get the results path of the scenario

        Returns
        -------
        Path
            The results path of the scenario
        """
        return self._results_path

    def run(self):
        """run direct impact models for the scenario"""
        os.makedirs(self.results_path, exist_ok=True)

        # Initiate the logger for all the integrator scripts.
        self._initiate_root_logger(
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
        self._close_root_logger_handlers()

    def __eq__(self, other):
        if not isinstance(other, Scenario):
            # don't attempt to compare against unrelated types
            return NotImplemented

        test1 = self.attrs.event == other.attrs.event
        test2 = self.attrs.projection == other.attrs.projection
        test3 = self.attrs.strategy == other.attrs.strategy
        return test1 & test2 & test3

    @staticmethod
    def _initiate_root_logger(filename):
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
    def _close_root_logger_handlers():
        """Close and remove all handlers from the root logger. This way,
        it is possible to delete the log file, which is not possible if
        the file is still open."""

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
