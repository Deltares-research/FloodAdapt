from pathlib import Path

from flood_adapt.database_builder.database_builder import DatabaseBuilder


def create_database(config: Path) -> None:
    """Create a new database from a configuration file or dictionary.

    Parameters
    ----------
    config : Path
        The path to the configuration file
    """
    DatabaseBuilder.from_file(config_path=config).build()
