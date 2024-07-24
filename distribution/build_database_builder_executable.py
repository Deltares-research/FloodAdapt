import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import PyInstaller.__main__  # noQA
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller==6.7"])
    import PyInstaller.__main__  # noQA

from PyInstaller.utils.hooks import collect_delvewheel_libs_directory  # noQA

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = Path(__file__).resolve().parents[0]
PROJECT_NAME = "FloodAdapt_Database_Builder"
BUILD_DIR = Path(DIST_ROOT, "build")
DIST_DIR = Path(DIST_ROOT, "dist")
SRC_DIR = Path(PROJECT_ROOT) / "flood_adapt"
SITE_PACKAGES_PATH = Path(sys.executable).parent / "Lib" / "site-packages"


def copy_shapely_libs():
    # This has to be done now as the hook-shapely.py script is not updated to handle this apparently
    shapely_dir = os.path.join(SITE_PACKAGES_PATH, "shapely")
    if not os.path.exists(shapely_dir):
        raise FileNotFoundError("Shapely not found in site-packages")

    shapely_libs_dir = os.path.join(SITE_PACKAGES_PATH, "Shapely.libs")
    if not os.path.exists(shapely_libs_dir):
        os.makedirs(shapely_libs_dir)

    dlls = [
        os.path.join(shapely_dir, "geos.dll"),
        os.path.join(shapely_dir, "geos_c.dll"),
    ]
    for dll in dlls:
        if not os.path.exists(dll):
            raise FileNotFoundError(f"{dll} not found in shapely")
        shutil.copy(src=dll, dst=shapely_libs_dir)


def run_pyinstaller() -> None:
    entry_point = SRC_DIR / "database_builder" / "create_database.py"
    spec_path = DIST_ROOT

    command = [
        str(entry_point),
        "--clean",
        "--noconfirm",
        f"--name={PROJECT_NAME}",
        f"--workpath={BUILD_DIR}",
        f"--distpath={DIST_DIR}",
        f"--specpath={spec_path}",
    ]

    command.append("--collect-all=flood_adapt")
    command.append("--recursive-copy-metadata=flood_adapt")
    command.append("--collect-all=rasterio")
    command.append("--collect-all=pyogrio")
    command.append("--collect-all=xugrid")
    command.append("--collect-all=hydromt")
    command.append("--recursive-copy-metadata=hydromt")
    command.append("--collect-all=hydromt_fiat")
    command.append("--recursive-copy-metadata=hydromt_fiat")
    # command.append("--collect-all=hydromt_sfincs")
    # command.append("--recursive-copy-metadata=hydromt_sfincs")
    command.append(f"--paths={SITE_PACKAGES_PATH}")
    templates_path = entry_point.parent / "templates"
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
