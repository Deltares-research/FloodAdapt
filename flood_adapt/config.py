import os
from pathlib import Path

import tomli


def set_database_root(database_root: Path) -> None:
    """
    Sets the root directory for the database.

    Args:
        database_root (str): The new root directory path.
    """
    if not Path(database_root).is_dir():
        raise ValueError(f"{database_root} is not a valid database root directory")
    os.environ["DATABASE_ROOT"] = str(database_root)


def set_system_folder(system_folder: Path) -> None:
    """
    Sets the system folder path.

    Args:
        system_folder (str): The new system folder path.
    """
    if not Path(system_folder).is_dir():
        raise ValueError(f"{system_folder} is not a valid system folder directory")
    os.environ["SYSTEM_FOLDER"] = str(system_folder)


def set_database_name(database_name: str) -> None:
    """
    Sets the database_name.

    Args:
        database_name (str): The new database name.
    """
    db_root = os.environ["DATABASE_ROOT"]
    full_database_path = Path(db_root, database_name)
    if not full_database_path.is_dir():
        raise ValueError(f"{full_database_path} is not a valid directory\n")
    os.environ["DATABASE_NAME"] = str(database_name)


def get_database_root() -> Path:
    """
    Gets the root directory for the database.

    Returns:
        Path: The path to the root of the database.
    """
    return Path(os.environ["DATABASE_ROOT"])


def get_system_folder() -> Path:
    """
    Gets the system folder path.

    Returns:
        Path: The system folder path.
    """
    return Path(os.environ["SYSTEM_FOLDER"])


def get_database_name() -> str:
    """
    Gets the database name.

    Returns:
        str: The database name.
    """
    return os.environ["DATABASE_NAME"]


def parse_config(config_path: Path) -> dict:
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    try:
        # Parse the config file
        if "DATABASE_ROOT" not in config:
            raise ValueError(f"DATABASE_ROOT not found in {config_path}")
        set_database_root(config["DATABASE_ROOT"])

        if "SYSTEM_FOLDER" not in config:
            raise ValueError(f"SYSTEM_FOLDER not found in {config_path}")
        set_system_folder(config["SYSTEM_FOLDER"])

        if "DATABASE_NAME" not in config:
            raise ValueError(f"DATABASE_NAME not found in {config_path}")
        set_database_name(config["DATABASE_NAME"])
        print(f"Default configuration loaded from {config_path}")

    except ValueError as e:
        full_error = f"""
        {e}
        Error parsing configuration toml file: {config_path}
        Please make sure the file is formatted correctly and contains the required fields.
        """
        raise ValueError(full_error)

    return config


def parse_user_input(
    database_root=None, system_folder=None, database_name=None
) -> None:
    """
    Parse the user input and set the corresponding configuration values.

    Parameters
    ----------
    database_root : str
        The root directory of the database.
    system_folder : str
        The system folder.
    database_name : str
        The name of the database.

    Returns
    -------
    None
    """
    # Set database_root if given
    if database_root is not None:
        set_database_root(database_root)
        print(f"database_root updated: {database_root}")

    # Set system folder if given
    if system_folder is not None:
        set_system_folder(system_folder)
        print(f"system_folder updated: {system_folder}")

    # Set database_name if given
    if database_name is not None:
        set_database_name(database_name)
        print(f"database_name updated: {database_name}")


def main() -> None:
    # Get the directory that contains the config.toml file (e.g. the one above this one)
    config_dir = Path(__file__).parent.parent

    # Get the path to the config.toml file
    config_path = config_dir / "config.toml"
    parse_config(config_path)


if __name__ == "__main__":
    main()
