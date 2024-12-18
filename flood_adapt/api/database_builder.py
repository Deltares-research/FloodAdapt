from flood_adapt.database_builder.create_database import main


def create_database(config: str | dict) -> None:
    """Create a new database from a configuration file or dictionary.

    Parameters
    ----------
    config : str | dict
        The path to the configuration file or the configuration dictionary.
    """
    main(config)
