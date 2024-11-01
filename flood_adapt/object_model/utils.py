import os
import shutil
from contextlib import contextmanager
from pathlib import Path

from flood_adapt.object_model.interface.path_builder import (
    ObjectDir,
    db_path,
)


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
