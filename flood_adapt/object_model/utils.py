import os
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
