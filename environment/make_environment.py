import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import yaml  # noQA
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml  # noQA


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WHEELS_DIR = PROJECT_ROOT / "environment" / "geospatial-wheels"

SUBPROCESS_KWARGS = {
    "shell": True,
    "check": True,
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "universal_newlines": True,
}

try:
    subprocess.run("conda info", **SUBPROCESS_KWARGS)
except subprocess.CalledProcessError:
    subprocess.run("conda init", **SUBPROCESS_KWARGS)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--name",
        required=True,
        default=False,
        dest="env_name",
        type=str,
        help="The name for the environment to be created. If it already exists, it will be removed and recreated from scratch.",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        default=False,
        dest="prefix",
        type=str,
        help="Creates the environment at prefix/name instead of the default conda location.",
    )
    parser.add_argument(
        "-e",
        "--editable",
        default=False,
        dest="editable",
        action="store_true",
        help="Do an editable install of the FloodAdapt-GUI and FloodAdapt packages instead of a regular one.",
    )
    parser.add_argument(
        "-d",
        "--optional-deps",
        default="none",
        dest="optional_deps",
        help="Install optional dependencies of FloodAdapt-GUI and FloodAdapt in addition the core ones. (linting, testing, etc.) Default is to not install any.",
    )
    parser.add_argument(
        "--project-root",
        default=None,
        type=str,
        dest="project_root",
        help="The root directory of the project. Default is 2 levels above this script. Usually named 'FloodAdapt'.",
    )

    args = parser.parse_args()
    return args


def write_env_yml(env_name: str):
    env = {
        "name": env_name,
        "channels": ["conda-forge"],
        "dependencies": ["python=3.10", "pip", {"pip": []}],
    }

    for wheel in os.listdir(WHEELS_DIR):
        wheel_path = os.path.join(WHEELS_DIR, wheel)
        env["dependencies"][-1]["pip"].append(wheel_path)

    with open("_environment.yml", "w") as f:
        yaml.dump(env, f)
    print(f"Temporary environment file created at: {PROJECT_ROOT / '_environment.yml'}")


def check_and_delete_conda_env(env_name, prefix=None):
    result = subprocess.run("conda env list", **SUBPROCESS_KWARGS)

    if env_name in result.stdout:
        print(f"Environment {env_name} already exists. Removing it now...")
        if prefix:
            subprocess.run(f"conda env remove -p {prefix} -y", **SUBPROCESS_KWARGS)
        else:
            subprocess.run(f"conda env remove -n {env_name} -y", **SUBPROCESS_KWARGS)


def create_env(
    env_name: str,
    prefix: str = None,
    editable: bool = False,
    optional_deps: str = None,
):
    if not PROJECT_ROOT.exists():
        raise FileNotFoundError(
            f"The FloodAdapt repository was not found in the expected location: {PROJECT_ROOT}"
        )

    write_env_yml(env_name)
    check_and_delete_conda_env(env_name, prefix=prefix)

    env_location = os.path.join(prefix, env_name) if prefix else env_name
    prefix_option = f"--prefix {env_location}" if prefix else ""
    create_command = f"conda env create -f _environment.yml {prefix_option}"

    activate_option = env_location if prefix else env_name
    activate_command = f"conda activate {activate_option}"

    editable_option = "-e" if editable else ""
    dependency_option = f"[{optional_deps}]" if optional_deps is not None else ""

    command_list = [
        "conda activate",
        create_command,
        activate_command,
        f"pip install {editable_option} {PROJECT_ROOT.as_posix()}{dependency_option} --no-cache-dir",
    ]
    command = " && ".join(command_list)

    print("Running commands:")
    [print(c) for c in command_list]

    print(f"\n\nBuilding environment {env_name}... This might take some time.\n\n")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    while process.poll() is None:
        print(process.stdout.readline())

    if process.returncode != 0:
        print(process.stderr.read())
        raise RuntimeError(
            f"Environment creation failed with return code {process.returncode}"
        )

    os.remove("_environment.yml")
    print(f"Environment {env_name} created successfully!")
    print(f"Activate it with:\n\n\t{activate_command}\n")


if __name__ == "__main__":
    args = parse_args()
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root).resolve()
        print(f"Using project root: {PROJECT_ROOT}")
        WHEELS_DIR = PROJECT_ROOT / "environment" / "geospatial-wheels"

        assert (
            PROJECT_ROOT.exists()
        ), f"Project root does not exist: {PROJECT_ROOT}. Please verify your project root."
        assert (
            PROJECT_ROOT / "flood_adapt"
        ).exists(), f"Project root {PROJECT_ROOT} does not contain the flood_adapt package. Please verify your project root."
        assert (
            WHEELS_DIR.exists()
        ), f"Wheels directory does not exist: {WHEELS_DIR}. Please verify your project root."

    create_env(
        env_name=args.env_name,
        prefix=args.prefix,
        editable=args.editable,
        optional_deps=args.optional_deps,
    )
