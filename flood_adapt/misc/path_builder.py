from enum import Enum
from pathlib import Path
from typing import Optional

from flood_adapt.config.config import Settings


class TopLevelDir(str, Enum):
    """Top level directories in the database."""

    input = "input"
    output = "output"
    static = "static"
    temp = "temp"


class ObjectDir(str, Enum):
    """The names for object directories at the second level of the database."""

    site = "site"

    benefit = "benefits"
    event = "events"
    strategy = "strategies"
    measure = "measures"
    projection = "projections"
    scenario = "scenarios"
    config = "config"

    # buyout = "measures"
    # elevate = "measures"
    # floodproof = "measures"
    # greening = "measures"
    # floodwall = "measures"
    # pump = "measures"


def db_path(
    top_level_dir: TopLevelDir = TopLevelDir.input,
    object_dir: Optional[ObjectDir] = None,
    obj_name: Optional[str] = None,
) -> Path:
    """Return an path to a database directory from arguments."""
    rel_path = Path(top_level_dir.value)
    if object_dir is not None:
        if isinstance(object_dir, ObjectDir):
            rel_path = rel_path / object_dir.value
        else:
            rel_path = rel_path / str(object_dir)

        if obj_name is not None:
            rel_path = rel_path / obj_name

    return Settings().database_path / rel_path
