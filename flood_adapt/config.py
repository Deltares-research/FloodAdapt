import os
from pathlib import Path

import tomli


def set_database_root(database_root) -> None:
    """
    Sets the root directory for the database.

    Args:
        database_root (str): The new root directory path.
    """
    if not Path(database_root).is_dir():
        raise ValueError(f"{database_root} is not a directory")
    os.environ["DATABASE_ROOT"] = database_root


def set_system_folder(system_folder) -> None:
    """
    Sets the system folder path.

    Args:
        system_folder (str): The new system folder path.
    """
    if not Path(system_folder).is_dir():
        raise ValueError(f"{system_folder} is not a directory")
    os.environ["SYSTEM_FOLDER"] = system_folder


def set_site_name(site_name) -> None:
    """
    Sets the site_name.

    Args:
        site_name (str): The new system folder path.
    """
    db_root = os.environ.get("DATABASE_ROOT")
    full_site_path = Path(db_root, site_name)
    if not full_site_path.is_dir():
        raise ValueError(f"{full_site_path} is not a directory")
    os.environ["SITE_NAME"] = site_name


def parse_config(config_path) -> dict:
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    # Parse the config file
    if "database_root" not in config:
        raise ValueError(f"database_root not found in {config_path}")
    set_database_root(config["database_root"])

    if "system_folder" not in config:
        raise ValueError(f"system_folder not found in {config_path}")
    set_system_folder(config["system_folder"])

    if "site_name" not in config:
        raise ValueError(f"site_name not found in {config_path}")
    set_site_name(config["site_name"])

    return config


def main() -> None:
    # Get the directory that contains the config.toml file (e.g. the one above this one)
    config_dir = Path(__file__).parent.parent

    # Get the path to the config.toml file
    config_path = config_dir / "config.toml"
    parse_config(config_path)


if __name__ == "__main__":
    main()
