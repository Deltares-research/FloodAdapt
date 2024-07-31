from abc import ABC

from deprecated import deprecated


class IDatabaseUser(ABC):
    """Abstract class for FloodAdapt classes that need to use / interact with the FloodAdapt database."""

    _database_instance = None

    @property
    def database(self):
        if self._database_instance is not None:
            return self._database_instance
        from flood_adapt.dbs_controller import Database  # noqa

        self._database_instance = Database()
        return self._database_instance

    @deprecated(
        version="0.2.0",
        reason="`database_input_path` is deprecated. Use the database attribute instead.",
    )
    @property
    def database_input_path(self):
        return self.database.input_path
