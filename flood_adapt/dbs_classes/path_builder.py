from enum import Enum
from pathlib import Path
from typing import Optional

from flood_adapt.config import Settings


class TopLevelDir(str, Enum):
    input = "input"
    output = "output"
    static = "static"
    temp = "temp"


class ObjectDir(str, Enum):
    site = "site"

    benefit = "benefits"
    event = "events"
    strategy = "strategies"
    measure = "measures"
    projection = "projections"
    scenario = "scenarios"

    buyout = "measures"
    elevate = "measures"
    floodproof = "measures"
    greening = "measures"
    floodwall = "measures"
    pump = "measures"


def db_path(
    top_level_dir: TopLevelDir = TopLevelDir.input,
    object_dir: Optional[ObjectDir] = None,
    obj_name: Optional[str] = None,
) -> Path:
    """Return an path to a database directory from arguments."""
    return Settings().database_path / rel_path(
        top_level_dir=top_level_dir, object_dir=object_dir, obj_name=obj_name
    )


def rel_path(
    top_level_dir: TopLevelDir = TopLevelDir.input,
    object_dir: Optional[ObjectDir] = None,
    obj_name: Optional[str] = None,
) -> Path:
    """Return a relative path to a directory from arguments."""
    _path = Path(top_level_dir.value)

    if object_dir is not None:
        if isinstance(object_dir, ObjectDir):
            _path = _path / object_dir.value
        else:
            _path = _path / str(object_dir)

        if obj_name is not None:
            _path = _path / obj_name

    return _path
