import os
import shutil
from contextlib import contextmanager
from pathlib import Path


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


def import_external_file(
    external_file: Path | str | os.PathLike, dst_dir: Path | str | os.PathLike
) -> Path:
    """Copy an external file to the destination directory.

    Parameters
    ----------
    external_file : Path | str | os.PathLike
        Path to the external file to be copied.
    dst_dir : Path | str | os.PathLike
        Path to the destination directory.

    Returns
    -------
    Path
        Path to the copied file.

    Raises
    ------
    FileNotFoundError
        If the external file does not exist.
    """
    external_file = Path(external_file).resolve()
    dst_dir = Path(dst_dir).resolve()
    if not external_file.exists():
        raise FileNotFoundError(
            f"Could not import file {external_file} as it does not exist."
        )
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(external_file, dst_dir / external_file.name)

    return dst_dir / external_file.name
