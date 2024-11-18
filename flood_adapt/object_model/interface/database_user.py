import logging
from abc import ABC

from flood_adapt.misc.log import FloodAdaptLogging


class IDatabaseUser(ABC):
    """Abstract class for FloodAdapt classes that need to use / interact with the FloodAdapt database."""

    _database_instance = None
    _logger = None

    @classmethod
    def get_logger(cls) -> logging.Logger:
        """Return the logger for the object."""
        if cls._logger is None:
            cls._logger = FloodAdaptLogging.getLogger(cls.__name__)
        return cls._logger

    @classmethod
    def get_database(cls):
        """Return the database for the object."""
        if cls._database_instance is None:
            from flood_adapt.dbs_classes.database import Database

            cls._database_instance = Database()
        return cls._database_instance

    @property
    def database(self):
        """Return the database for the object."""
        return self.get_database()

    @property
    def logger(self) -> logging.Logger:
        """Return the logger for the object."""
        return self.get_logger()
