import tomli
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
    

# def write_config(file_path: Union[str, Path]):
#     #LABLA
