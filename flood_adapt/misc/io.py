import sys
from pathlib import Path

import tomli_w

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def read_toml(path: Path) -> dict:
    """Read a TOML file and return its contents as a dictionary.

    Parameters
    ----------
    path : Path
        Path to the toml file.

    Returns
    -------
    dict
        The data read from the toml file.
    """
    with open(path, mode="rb") as fp:
        data = tomllib.load(fp)
    return data


def write_toml(data: dict, path: Path) -> None:
    """Write a dictionary to a toml file.

    Parameters
    ----------
    data : dict
        The data to write to the toml file.
    path : Path
        Path to the toml file.
    """
    with open(path, mode="wb") as fp:
        tomli_w.dump(data, fp)
