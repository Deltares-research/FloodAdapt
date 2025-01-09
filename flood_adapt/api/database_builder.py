from pathlib import Path

from flood_adapt.database_builder.create_database import DatabaseBuilder


def create_database(config: Path) -> None:
    """Create a new database from a configuration file or dictionary.

    Parameters
    ----------
    config : Path
        The path to the configuration file
    """
    DatabaseBuilder(config_path=config).build()
