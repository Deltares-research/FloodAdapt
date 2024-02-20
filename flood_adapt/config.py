import os
from pathlib import Path
from typing import Union

import tomli


def set_database_root(database_root: Path, overwrite: bool = True) -> None:
    """
    Sets the database root path.

    Parameters
    ----------
    database_root : Path
        The absolute new database_root path.
    overwrite : bool, optional
        If False, it will only be set if it is not already set.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the provided database root is not a valid directory.
    """
    abs_database_root = Path(database_root).resolve()
    if not Path(abs_database_root).is_dir():
        raise ValueError(f"{abs_database_root} is not a valid database root directory")

    if get_database_root() is None:
        os.environ["DATABASE_ROOT"] = str(abs_database_root)
        print(f"database_root set: {abs_database_root}")
    elif overwrite:
        print(f"database_root overwritten: {abs_database_root}")
        os.environ["DATABASE_ROOT"] = str(abs_database_root)


def set_system_folder(system_folder: Path, overwrite: bool = True) -> None:
    """
    Sets the system folder path.

    Parameters
    ----------
    system_folder : Path
        The new system folder path.
    overwrite : bool, optional
        If False, it will only be set if it is not already set.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the provided system folder is not a valid directory.
    """
    abs_system_folder = Path(system_folder).resolve()
    if not Path(abs_system_folder).is_dir():
        raise ValueError(f"{abs_system_folder} is not a valid system folder directory")

    if get_system_folder() is None:
        os.environ["SYSTEM_FOLDER"] = str(abs_system_folder)
        print(f"system_folder set: {abs_system_folder}")
    elif overwrite:
        print(f"system_folder overwritten: {abs_system_folder}")
        os.environ["SYSTEM_FOLDER"] = str(abs_system_folder)


def set_database_name(database_name: str, overwrite: bool = True) -> None:
    """
    Sets the database_name.

    Parameters
    ----------
    database_name : str
        The new database name.
    overwrite : bool, optional
        If False, it will only be set if it is not already set.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If DATABASE_ROOT is not set or if the provided database_name is not a valid directory in DATABASE_ROOT.
    """
    db_root = get_database_root()
    if db_root is None:
        raise ValueError(
            "DATABASE_ROOT is not set, set it before setting DATABASE_NAME\n"
        )

    full_database_path = Path(db_root, database_name)
    if not full_database_path.is_dir():
        raise ValueError(f"{full_database_path} is not a valid directory\n")

    if get_database_name() is None:
        os.environ["DATABASE_NAME"] = str(database_name)
        print(f"database_name set: {database_name}")
    elif overwrite:
        print(f"database_name overwritten: {database_name}")
        os.environ["DATABASE_NAME"] = str(database_name)


def get_database_root() -> Union[Path, None]:
    """
    Gets the root directory for the database.

    Returns
    -------
    Path or None
        The path to the root of the database if the DATABASE_ROOT environment variable is set,
        None otherwise.
    """
    try:
        return Path(os.environ["DATABASE_ROOT"])
    except KeyError:
        return None


def get_system_folder() -> Union[Path, None]:
    """
    Gets the system folder path.

    Returns
    -------
    Path or None
        The system folder path if the SYSTEM_FOLDER environment variable is set, otherwise None.
    """
    try:
        return Path(os.environ["SYSTEM_FOLDER"])
    except KeyError:
        return None


def get_database_name() -> Union[str, None]:
    """
    Gets the database name.

    Returns
    -------
    str or None
        The database name if the DATABASE_NAME environment variable is set, otherwise None.
    """
    try:
        return Path(os.environ["DATABASE_NAME"])
    except KeyError:
        return None


def parse_config(config_path: Path, overwrite: bool = True) -> dict:
    """
    Parse the configuration file and return the parsed configuration dictionary.

    Parameters
    ----------
    config_path : Path
        The path to the configuration file.
    overwrite : bool, optional
        Flag indicating whether to overwrite existing configuration values, defaults to True.

    Returns
    -------
    dict
        The parsed configuration dictionary.

    Raises
    ------
    ValueError
        If required configuration values are missing or if there is an error parsing the configuration file.
    """
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    config_base_dir = config_path.parent

    try:
        # Parse the config file
        if "DATABASE_ROOT" not in config:
            raise ValueError(f"DATABASE_ROOT not found in {config_path}")
        database_root = config_base_dir / config["DATABASE_ROOT"]
        set_database_root(database_root, overwrite=overwrite)

        if "SYSTEM_FOLDER" not in config:
            raise ValueError(f"SYSTEM_FOLDER not found in {config_path}")
        system_folder = config_base_dir / config["SYSTEM_FOLDER"]
        set_system_folder(system_folder, overwrite=overwrite)

        if "DATABASE_NAME" not in config:
            raise ValueError(f"DATABASE_NAME not found in {config_path}")
        set_database_name(config["DATABASE_NAME"], overwrite=overwrite)

        if overwrite:
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
    database_root : str, optional
        The absolute path to the root directory of the database.
    system_folder : str, optional
        The absolute path to the system folder.
    database_name : str, optional
        The name of the database.
    overwrite : bool, optional
        Whether to overwrite existing configuration values. Default is True.

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

    if any(val is not None for val in [database_root, system_folder, database_name]):
        print("Parsed user input successfully")


def main() -> None:
    # Get the directory that contains the config.toml file (e.g. the one above this one)
    config_dir = Path(__file__).parent.parent

    # Get the path to the config.toml file
    config_path = config_dir / "config.toml"
    parse_config(config_path)


if __name__ == "__main__":
    main()
