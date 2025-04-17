from pathlib import Path

from flood_adapt.database_builder.database_builder import ConfigModel, DatabaseBuilder


def create_database(config_path: Path) -> None:
    """Create a new database from a configuration file or dictionary.

    Parameters
    ----------
    config : Path
        The path to the configuration file
    """
    config = ConfigModel.read(config_path)

    DatabaseBuilder(config=config).build()
