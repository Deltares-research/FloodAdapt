import os
from pathlib import Path
from typing import Union

import tomli


def set_database_root(database_root: Path, overwrite: bool = True) -> None:
    """
    Sets the root directory for the database.

    Args:
        database_root (str): The new root directory path.
        overwrite (bool): If false, it will only be set if it is not already set.
    """
    abs_database_root = Path(database_root).resolve()
    if not Path(abs_database_root).is_dir():
        raise ValueError(f"{abs_database_root} is not a valid database root directory")

    if overwrite:
        os.environ["DATABASE_ROOT"] = str(abs_database_root)
        print(f"database_root updated: {abs_database_root}")
    else:
        if get_database_root() is None:
            os.environ["DATABASE_ROOT"] = str(abs_database_root)
            print(f"database_root updated: {abs_database_root}")


def set_system_folder(system_folder: Path, overwrite: bool = True) -> None:
    """
    Sets the system folder path.

    Args:
        system_folder (str): The new system folder path.
    """
    abs_system_folder = Path(system_folder).resolve()
    if not Path(abs_system_folder).is_dir():
        raise ValueError(f"{abs_system_folder} is not a valid system folder directory")

    if overwrite:
        os.environ["SYSTEM_FOLDER"] = str(abs_system_folder)
        print(f"system_folder updated: {abs_system_folder}")

    else:
        if get_system_folder() is None:
            os.environ["SYSTEM_FOLDER"] = str(abs_system_folder)
            print(f"system_folder updated: {abs_system_folder}")


def set_database_name(database_name: str, overwrite: bool = True) -> None:
    """
    Sets the database_name.

    Args:
        database_name (str): The new database name.
    """
    db_root = get_database_root()
    full_database_path = Path(db_root, database_name)
    if not full_database_path.is_dir():
        raise ValueError(f"{full_database_path} is not a valid directory\n")

    if overwrite:
        os.environ["DATABASE_NAME"] = str(database_name)
        print(f"database_name updated: {database_name}")
    else:
        if get_database_name() is None:
            os.environ["DATABASE_NAME"] = str(database_name)
            print(f"database_name updated: {database_name}")


def get_database_root() -> Union[Path, None]:
    """
    Gets the root directory for the database.

    Returns:
        Path: The path to the root of the database.
        None: If the DATABASE_ROOT environment variable is not set.
    """
    try:
        return Path(os.environ["DATABASE_ROOT"])
    except KeyError:
        return None


def get_system_folder() -> Union[Path, None]:
    """
    Gets the system folder path.

    Returns:
        Path: The system folder path.
        None: If the SYSTEM_FOLDER environment variable is not set.
    """
    try:
        return Path(os.environ["SYSTEM_FOLDER"])
    except KeyError:
        return None


def get_database_name() -> Union[str, None]:
    """
    Gets the database name.

    Returns:
        str: The database name.
        None: If the DATABASE_NAME environment variable is not set.
    """
    try:
        return Path(os.environ["DATABASE_NAME"])
    except KeyError:
        return None


def parse_config(config_path: Path, overwrite: bool = True) -> dict:
    with open(config_path, "rb") as f:
        config = tomli.load(f)
    try:
        # Parse the config file
        if "DATABASE_ROOT" not in config:
            raise ValueError(f"DATABASE_ROOT not found in {config_path}")
        set_database_root(config["DATABASE_ROOT"], overwrite=overwrite)

        if "SYSTEM_FOLDER" not in config:
            raise ValueError(f"SYSTEM_FOLDER not found in {config_path}")
        set_system_folder(config["SYSTEM_FOLDER"], overwrite=overwrite)

        if "DATABASE_NAME" not in config:
            raise ValueError(f"DATABASE_NAME not found in {config_path}")
        set_database_name(config["DATABASE_NAME"], overwrite=overwrite)
        print(f"Configuration loaded from {config_path}")

    except ValueError as e:
        full_error = f"""
        {e}
        Error parsing configuration toml file: {config_path}
        Please make sure the file is formatted correctly and contains the required fields.
        """
        raise ValueError(full_error)

    return config


def parse_user_input(
    database_root=None, system_folder=None, database_name=None, overwrite=True
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
        set_database_root(database_root, overwrite=overwrite)

    # Set system folder if given
    if system_folder is not None:
        set_system_folder(system_folder, overwrite=overwrite)

    # Set database_name if given
    if database_name is not None:
        set_database_name(database_name, overwrite=overwrite)


def main() -> None:
    # Get the directory that contains the config.toml file (e.g. the one above this one)
    config_dir = Path(__file__).parent.parent

    # Get the path to the config.toml file
    config_path = config_dir / "config.toml"
    parse_config(config_path)


if __name__ == "__main__":
    main()
