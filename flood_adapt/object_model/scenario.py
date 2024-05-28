import gc
import logging
import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w

from flood_adapt.object_model.interface.scenarios import IScenario, ScenarioModel


class Scenario(IScenario):
    """class holding all information related to a scenario"""

    attrs: ScenarioModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Scenario from toml file"""

        obj = Scenario()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = ScenarioModel.parse_obj(toml)
        # if scenario is created by path use that to get to the database path
        obj.database_input_path = Path(filepath).parents[2]
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any], database_input_path: os.PathLike):
        """create Scenario from object, e.g. when initialized from GUI"""

        obj = Scenario()
        obj.attrs = ScenarioModel.parse_obj(data)
        obj.database_input_path = database_input_path
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """save Scenario to a toml file"""
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

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
