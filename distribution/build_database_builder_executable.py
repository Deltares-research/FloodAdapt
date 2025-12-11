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
BUILD_DIR = DIST_ROOT / "build"
DIST_DIR = DIST_ROOT / "dist"
EXE_SYSTEM_DIR = DIST_DIR / PROJECT_NAME / "_internal" / "flood_adapt" / "system"
SRC_DIR = PROJECT_ROOT / "flood_adapt"
SITE_PACKAGES_PATH = Path(sys.executable).parent / "Lib" / "site-packages"
ENTRY_POINT = SRC_DIR / "database_builder" / "database_builder.py"
SYSTEM_FOLDER = SRC_DIR / "system"

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


def copy_system_folder() -> None:
    """Copy the system folder to the executable."""
    if not SYSTEM_FOLDER.exists():
        raise FileNotFoundError(
            f"System folder not found. Ensure this path exists: {SYSTEM_FOLDER}"
        )
    if not (SYSTEM_FOLDER / "fiat").exists():
        raise FileNotFoundError(
            f"System folder does not contain the 'fiat' directory. Ensure this path exists: {SYSTEM_FOLDER / 'fiat'}"
        )
    if not (SYSTEM_FOLDER / "sfincs").exists():
        raise FileNotFoundError(
            f"System folder does not contain the 'sfincs' directory. Ensure this path exists: {SYSTEM_FOLDER / 'sfincs'}"
        )
    shutil.copytree(SYSTEM_FOLDER, EXE_SYSTEM_DIR)


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


def get_tomli_binaries() -> list[tuple[str, str]]:
    """
    Python versions >3.10, this SHA256__mypyc.pyd file is not included by pyinstaller.

    See https://github.com/hukkin/tomli/issues/255.

    This doesnt solve it, but its a workaround to include the file in the hidden imports
    """
    import glob
    import sysconfig

    site_packages = sysconfig.get_paths()["purelib"]
    pattern = os.path.join(site_packages, "*__mypyc.*")
    files = [(f, ".") for f in glob.glob(pattern)]
    if not files:
        raise FileNotFoundError(
            f"No __mypyc files found in site-packages at {site_packages}"
        )
    print(f"Found __mypyc files: {files}")
    return files


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

    for binary, dest in get_tomli_binaries():
        command.append(f"--add-binary={binary}:{dest}")

    command.append(f"--paths={SITE_PACKAGES_PATH}")
    templates_path = ENTRY_POINT.parent / "templates"
    command.append(f"--add-data={templates_path}:templates")
    PyInstaller.__main__.run(command)

    copy_system_folder()

    print("\nFinished making the executable for the FloodAdapt database builder!")
    print(f"\nExecutable can be found at: {DIST_DIR / PROJECT_NAME}\n\n")


def main() -> None:
    copy_shapely_libs()
    # compile the executable using PyInstaller
    run_pyinstaller()


if __name__ == "__main__":
    main()
