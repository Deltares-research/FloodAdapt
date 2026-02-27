import os
from pathlib import Path
import shutil
import sys
from flood_adapt.flood_adapt import FloodAdapt

def clean_database(database_dir: Path):
    EXCLUDES = [
        "test_set",
        "current",
        "no_measures",
    ]
    for _dir in os.listdir(database_dir / "input"):
        obj_dir = database_dir / "input" / _dir
        for _subdir in os.listdir(obj_dir):
            if _subdir in EXCLUDES:
                print(f"Skipping deleting excluded directory: {obj_dir / _subdir}")
                continue
            subdir_path = obj_dir / _subdir
            shutil.rmtree(subdir_path)
            print(f"Removed directory: {subdir_path}")

    for _dir in ["output", "temp"]:
        dir_path = database_dir / _dir
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"Removed directory: {dir_path}")

    # Validate
    settings = Settings(DATABASE_ROOT=database_dir.parent, DATABASE_NAME=database_dir.name)
    settings.export_to_env()
    FloodAdapt(settings.database_path)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python clean_database.py <database_directory>")
        sys.exit(1)

    database_dir = Path(sys.argv[1]).resolve()
    if not database_dir.exists() or not database_dir.is_dir():
        print(f"Error: The specified directory '{database_dir}' does not exist or is not a directory.")
        sys.exit(1)

    clean_database(database_dir)
