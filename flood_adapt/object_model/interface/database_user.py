import logging
from abc import ABC

from flood_adapt.misc.log import FloodAdaptLogging


class DatabaseUser(ABC):
    """Abstract class for FloodAdapt classes that need to use / interact with the FloodAdapt database."""

    _database_instance = None
    _logger = None

    @property
    def database(self):
        """Return the database for the object."""
        if self._database_instance is None:
            from flood_adapt.dbs_classes.database import Database

            self._database_instance = Database()
        return self._database_instance

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for the object."""
        if self._logger is None:
            self._logger = FloodAdaptLogging.getLogger(self.__class__.__name__)
        return self._logger
