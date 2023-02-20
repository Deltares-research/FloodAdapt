import tomli, tomli_w
from typing import Union
from pathlib import Path


def read_config(file_path: Union[str, Path]) -> dict:
    """Generic function to read toml config files and return a dict.

    Args:
        file_path (Union[str, Path]): Path to .toml file.

    Returns:
        dict: Dictionary created from .toml file.
    """
    with open(file_path, mode="rb") as fp:
        config = tomli.load(fp)
    return config
    

def write_config(config: dict, file_path: Union[str, Path]) -> None:
    """Generic function to write a config file to .toml.

    Args:
        config (dict): A configuration dictionary.
        file_path (Union[str, Path]): The path to write the configuration file to, with .toml extension.
    """
    with open(file_path, mode="wb") as fp:
        tomli_w.dump(config, fp)


def validate_config(config: dict) -> bool:
    """Validates the configuration file. TODO: explain further what exactly is validated.

    Args:
        config (dict): A configuration dictionary.

    Returns:
        bool: True if the configuraton if valid and False if the configuration is invalid.
    """
    if config:
        # TODO: add the validation steps here.
        return True
