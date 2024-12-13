import argparse
import subprocess
from pathlib import Path
from typing import Optional

WHEELS_DIR = Path(__file__).parent / "geospatial-wheels"
BACKEND_ROOT = WHEELS_DIR.parents[1]

SUBPROCESS_KWARGS = {
    "shell": True,
    "check": True,
    "stdout": subprocess.PIPE,
    "stderr": subprocess.PIPE,
    "universal_newlines": True,
}


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
        default=None,
        dest="optional_deps",
        help="Install optional dependencies of FloodAdapt-GUI and FloodAdapt in addition the core ones. Must be one of: [dev, docs, build, all]. Default is to not install any.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        dest="debug",
        help="Print debug logs during the environment creation process.",
    )

    args = parser.parse_args()
    return args


def check_and_delete_conda_env(env_name: str):
    result = subprocess.run(["conda", "env", "list"], **SUBPROCESS_KWARGS)

    if env_name in result.stdout:
        print(f"Environment {env_name} already exists. Removing it now...")
        subprocess.run(
            ["conda", "env", "remove", "-n", env_name, "-y"], **SUBPROCESS_KWARGS
        )


def create_env(
    env_name: str,
    editable: bool = False,
    optional_deps: Optional[str] = None,
    debug: bool = False,
):
    if not (BACKEND_ROOT / "pyproject.toml").exists():
        raise FileNotFoundError(
            f"Expected a pyproject.toml file at: {BACKEND_ROOT / 'pyproject.toml'}"
        )

    try:
        subprocess.run("conda info", **SUBPROCESS_KWARGS)
    except subprocess.CalledProcessError:
        subprocess.run("conda init", **SUBPROCESS_KWARGS)

    check_and_delete_conda_env(env_name)

    ENV_YML = BACKEND_ROOT / "environment" / "_environment.yml"
    DEBUG_LOGFILE = Path(__file__).parent / f"{env_name}_debug.log"

    create_args = ["conda", "env", "create", "-n", env_name, "-f", str(ENV_YML)]
    activate_args = ["conda", "activate", env_name]

    dependency_option = f"[{optional_deps}]" if optional_deps is not None else ""
    debug_log_option = ["-v", "-v", "-v", "--log", str(DEBUG_LOGFILE)] if debug else ""
    editable_option = "-e" if editable else ""
    pip_install_args = [
        "pip",
        "install",
        editable_option,
        f"{BACKEND_ROOT}{dependency_option}",
        debug_log_option,
        "--no-cache-dir",
    ]

    command_list = [
        " ".join(["conda", "activate"]),
        " ".join(create_args),
        " ".join(activate_args),
        " ".join(pip_install_args),
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

    while process.poll() is None and process.stdout:
        print(process.stdout.readline(), end="")

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
    print(f"Activate it with:\n\n\t{' '.join(activate_args)}\n")


if __name__ == "__main__":
    args = parse_args()

    create_env(
        env_name=args.env_name,
        editable=args.editable,
        optional_deps=args.optional_deps,
    )
