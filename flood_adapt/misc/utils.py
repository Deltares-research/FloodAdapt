import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Union

import geopandas as gpd
from pydantic import BeforeValidator

from flood_adapt.misc.log import FloodAdaptLogging

logger = FloodAdaptLogging.getLogger(__name__)


@contextmanager
def modified_environ(*remove, **update):
    """
    Temporarily updates the ``os.environ`` dictionary in-place.

    From https://github.com/laurent-laporte-pro/stackoverflow-q2059482/blob/master/demo/environ_ctx.py

    The ``os.environ`` dictionary is updated in-place so that the modification
    is sure to work in all situations.

    :param remove: Environment variables to remove.
    :param update: Dictionary of environment variables and values to add/update.
    """
    env = os.environ
    update = update or {}
    remove = remove or []

    # List of environment variables being updated or removed.
    stomped = (set(update.keys()) | set(remove)) & set(env.keys())
    # Environment variables and values to restore on exit.
    update_after = {k: env[k] for k in stomped}
    # Environment variables and values to remove on exit.
    remove_after = frozenset(k for k in update if k not in env)

    try:
        env.update(update)
        [env.pop(k, None) for k in remove]
        yield
    finally:
        env.update(update_after)
        [env.pop(k) for k in remove_after]


@contextmanager
def cd(newdir: Path):
    prevdir = Path().cwd()
    os.chdir(newdir)
    try:
        yield
    finally:
        os.chdir(prevdir)


def write_finished_file(path: Path):
    if not path.exists():
        path.mkdir(parents=True)
    with open(Path(path) / "finished.txt", "w") as f:
        f.write("run finished")


def finished_file_exists(path: Path):
    return (Path(path) / "finished.txt").exists()


def save_file_to_database(
    src_file: Path | str | os.PathLike, dst_dir: Path | str | os.PathLike
) -> Path:
    """Save a file to the database.

    Geospatial files (`.shp`, `.geojson`, `.gpkg`), are read, converted, and saved in standard format (EPSG:4326).
    Other files are simply copied.

    Parameters
    ----------
    src_file : Path | str | os.PathLike
        Path to the file to be copied.
    dst_dir : Path | str | os.PathLike
        Path to the destination directory.

    Returns
    -------
    Path
        Path to the copied file

    Raises
    ------
    FileNotFoundError
        If the src_file does not exist at the given path
    """
    src_file = Path(src_file).resolve()
    dst_file = Path(dst_dir).resolve() / src_file.name

    if not src_file.exists():
        raise FileNotFoundError(
            f"Failed to find {src_file} when saving external file to the database as it does not exist."
        )
    if src_file == dst_file:
        return dst_file
    elif dst_file.exists():
        match dst_file.suffix:
            case ".shp":
                for file in list(dst_file.parent.glob(f"{dst_file.stem}.*")):
                    os.remove(file)
            case _:
                os.remove(dst_file)

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    match src_file.suffix:
        case ".shp":
            # to_file docstring: `If no extension is specified, it saves ESRI Shapefile to a folder.`
            gpd.read_file(src_file).to_crs(epsg=4326).to_file(dst_file.with_suffix(""))
        case ".geojson" | ".gpkg":
            gpd.read_file(src_file).to_crs(epsg=4326).to_file(dst_file)
        case _:
            shutil.copy2(src_file, dst_file)

    return dst_file


def copy_file_to_output_dir(file_path: Path, output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    if file_path == output_dir / file_path.name:
        return file_path
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file_path, output_dir)
    return output_dir / file_path.name


def validate_file_extension(allowed_extensions: list[str]):
    """Validate the extension of the given path has one of the given suffixes.

    Examples
    --------
    >>> from pydantic import BaseModel
    >>> from pathlib import Path
    >>> from typing import Annotated

    >>> class MyClass(BaseModel):
    >>>     csv_path: Annotated[Path, validate_file_extension([".csv"])]
    """

    def _validator(value: Union[Path, str, os.PathLike]) -> Path:
        value = Path(value)
        if value.suffix not in allowed_extensions:
            raise ValueError(
                f"Invalid file extension: {value}. Allowed extensions are {', '.join(allowed_extensions)}."
            )
        return value

    return BeforeValidator(_validator)
