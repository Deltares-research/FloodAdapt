from abc import ABC


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

    @property
    def database_input_path(self):  # TODO deprecate
        return self.database.input_path
