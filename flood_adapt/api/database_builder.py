from pathlib import Path

from flood_adapt.database_builder.create_database import DatabaseBuilder


def create_database(config: Path) -> None:
    """Create a new database from a configuration file or dictionary.

    Parameters
    ----------
    config : str | dict
        The path to the configuration file or the configuration dictionary.
    """
    DatabaseBuilder(config_path=config).build()
