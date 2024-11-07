from abc import ABC

from flood_adapt.misc.log import FloodAdaptLogging


class IDatabaseUser(ABC):
    """Abstract class for FloodAdapt classes that need to use / interact with the FloodAdapt database."""

    _database_instance = None
    _logger = None

    @property
    def database(self):
        if self._database_instance is not None:
            return self._database_instance
        from flood_adapt.dbs_classes.database import Database  # noqa

        self._database_instance = Database()
        return self._database_instance

    @property
    def logger(self):
        if self._logger is not None:
            return self._logger
        self._logger = FloodAdaptLogging.getLogger(self.__class__.__name__)
        return self._logger
