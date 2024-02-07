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


def set_site_name(site_name: str) -> None:
    """
    Sets the site_name.

    Args:
        site_name (str): The new system folder path.
    """
    db_root = os.environ.get("DATABASE_ROOT")
    full_site_path = Path(db_root, site_name)
    if not full_site_path.is_dir():
        raise ValueError(f"{full_site_path} is not a valid site directory\n")
    os.environ["SITE_NAME"] = str(site_name)


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

        if "SITE_NAME" not in config:
            raise ValueError(f"SITE_NAME not found in {config_path}")
        set_site_name(config["SITE_NAME"])

    except ValueError as e:
        full_error = f"""
        {e}\n
        Error parsing configuration toml file: {config_path}\n
        Please make sure the file is formatted correctly and contains the required fields.
        """
        raise ValueError(full_error)

    return config


def main() -> None:
    # Get the directory that contains the config.toml file (e.g. the one above this one)
    config_dir = Path(__file__).parent.parent

    # Get the path to the config.toml file
    config_path = config_dir / "config.toml"
    parse_config(config_path)


if __name__ == "__main__":
    main()
