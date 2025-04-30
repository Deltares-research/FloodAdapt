import os
import shutil
import sys
from pathlib import Path

try:
    import PyInstaller.__main__  # noQA
except ImportError as e:
    raise ImportError(
        "PyInstaller is not installed. Please install it using 'pip install .[build]'."
    ) from e


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = Path(__file__).resolve().parents[0]
PROJECT_NAME = "FloodAdapt_Database_Builder"
BUILD_DIR = Path(DIST_ROOT, "build")
DIST_DIR = Path(DIST_ROOT, "dist")
SRC_DIR = Path(PROJECT_ROOT) / "flood_adapt"
SITE_PACKAGES_PATH = Path(sys.executable).parent / "Lib" / "site-packages"
ENTRY_POINT = SRC_DIR / "database_builder" / "database_builder.py"

# Dependencies to include in the executable
DEPENDENCIES = [
    "flood_adapt",
    "rasterio",
    "setuptools",
    "pyogrio",
    "xugrid",
    "hydromt",
    "hydromt_fiat",
    "hydromt_sfincs",
    "scipy",
]


def copy_shapely_libs():
    # This has to be done now as the hook-shapely.py script is not updated to handle this apparently
    shapely_dir = Path(SITE_PACKAGES_PATH, "shapely")
    if not os.path.exists(shapely_dir):
        raise FileNotFoundError("Shapely not found in site-packages")

    shapely_libs_dir = Path(SITE_PACKAGES_PATH, "Shapely.libs")
    if not os.path.exists(shapely_libs_dir):
        os.makedirs(shapely_libs_dir)

    # The (outdated) hook for shapely expects the .dll files to be in the shapely.libs directory, so we have to copy them there
    if not shapely_libs_dir.exists():
        shapely_libs_dir.mkdir(exist_ok=True)
        for file in shapely_dir.iterdir():
            if file.suffix == ".dll" and "geos" in file.name:
                shutil.copy2(src=file, dst=shapely_libs_dir)


def run_pyinstaller() -> None:
    command = [
        str(ENTRY_POINT),
        "--clean",
        "--noconfirm",
        f"--name={PROJECT_NAME}",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_DIR}",
        f"--specpath={DIST_ROOT}",
    ]

    for dep in DEPENDENCIES:
        command.append(f"--collect-all={dep}")
        command.append(f"--recursive-copy-metadata={dep}")

    command.append(f"--paths={SITE_PACKAGES_PATH}")
    templates_path = ENTRY_POINT.parent / "templates"
    command.append(f"--add-data={templates_path}:templates")
    PyInstaller.__main__.run(command)

    print("\nFinished making the executable for the FloodAdapt database builder!")
    print(f"\nExecutable can be found at: {DIST_DIR / PROJECT_NAME}\n\n")


def main() -> None:
    copy_shapely_libs()
    # compile the executable using PyInstaller
    run_pyinstaller()


if __name__ == "__main__":
    main()
