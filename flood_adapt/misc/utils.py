import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Union

from pydantic import BeforeValidator

from flood_adapt.misc.path_builder import (
    ObjectDir,
    db_path,
)


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


def resolve_filepath(
    object_dir: ObjectDir, obj_name: str, path: Path | str | os.PathLike
) -> Path:
    """
    Determine whether a given path is an external file or a file in the database.

    Users can set the path to a file in the database directly, meaning it will be an absolute path.
    Users can also read the path from loading a toml file, meaning it will be a filename relative to the toml file.

    Parameters
    ----------
    object_dir : ObjectDir
        The directory name of the object in the database.
    obj_name : str
        The name of the object.
    path : Union[Path, str, os.PathLike]
        The path to the file, which can be an absolute path or a relative path.

    Returns
    -------
    Path
        The resolved path to the file.

    Raises
    ------
    FileNotFoundError
        If the file does not exist in either the provided path or the database path.
    """
    _path = Path(path)
    if str(_path) == _path.name:
        # this is a filename, so it is in the database
        src_path = db_path(object_dir=object_dir, obj_name=obj_name) / path
    else:
        # this is a path, so it is an external file
        src_path = Path(path)
    return src_path


def save_file_to_database(
    src_file: Path | str | os.PathLike, dst_dir: Path | str | os.PathLike
) -> Path:
    """Save a file to the database.

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
        if dst_file.suffix == ".shp":
            for file in list(dst_file.parent.glob(f"{dst_file.stem}.*")):
                os.remove(file)
        else:
            os.remove(dst_file)

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    if src_file.suffix == ".shp":
        for file in list(src_file.parent.glob(f"{src_file.stem}.*")):
            shutil.copy2(file, dst_file.parent.joinpath(file.name))
    else:
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
