import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml  # noQA
except Exception:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
    import yaml  # noQA


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / "FloodAdapt"
WHEELS_DIR = BACKEND_ROOT / "environment" / "geospatial-wheels"

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


def check_and_delete_conda_env(env_name: str, prefix: Optional[str] = None):
    result = subprocess.run("conda env list", **SUBPROCESS_KWARGS)

    if env_name in result.stdout:
        print(f"Environment {env_name} already exists. Removing it now...")
        if prefix:
            subprocess.run(f"conda env remove -p {prefix} -y", **SUBPROCESS_KWARGS)
        else:
            subprocess.run(f"conda env remove -n {env_name} -y", **SUBPROCESS_KWARGS)


def create_env(
    env_name: str,
    prefix: Optional[str] = None,
    editable: bool = False,
    optional_deps: Optional[str] = None,
):
    if not BACKEND_ROOT.exists():
        raise FileNotFoundError(
            f"The FloodAdapt repository was not found in the expected location: {BACKEND_ROOT}"
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
        f"pip install {editable_option} {BACKEND_ROOT.as_posix()}{dependency_option} --no-cache-dir",
    ]
    command = " && ".join(command_list)

    print("Running commands:")
    [print(c) for c in command_list]
    Path.cwd()

    print(f"\n\nBuilding environment {env_name}... This might take some time.\n\n")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    while process.poll() is None and process.stdout:
        print(process.stdout.readline(), end="")

    os.remove("_environment.yml")

    if process.returncode != 0:
        if process.stderr:
            print(process.stderr.read())

        raise subprocess.CalledProcessError(
            process.returncode,
            command,
            process.stdout.read() if process.stdout else None,
            process.stderr.read() if process.stderr else None,
        )

    print(f"Environment {env_name} created successfully!")
    print(f"Activate it with:\n\n\t{activate_command}\n")


if __name__ == "__main__":
    args = parse_args()

    create_env(
        env_name=args.env_name,
        prefix=args.prefix,
        editable=args.editable,
        optional_deps=args.optional_deps,
    )
