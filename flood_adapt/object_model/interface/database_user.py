from abc import ABC


class DatabaseUser(ABC):
    """Abstract class for FloodAdapt classes that need to use / interact with the Singleton FloodAdapt database through the lazy-loading self.database property."""

    _database_instance = None

    @property
    def database(self):
        """Return the database for the object."""
        if self._database_instance is None:
            from flood_adapt.dbs_classes.database import Database

            self._database_instance = Database()
        return self._database_instance
