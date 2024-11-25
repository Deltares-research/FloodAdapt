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


WHEELS_DIR = Path(__file__).parent / "geospatial-wheels"

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
        default="flood_adapt",
        dest="env_name",
        help="The name for the environment to be created. If it already exists, it will be removed and recreated from scratch.",
    )
    parser.add_argument(
        "-p",
        "--prefix",
        default="",
        dest="prefix",
        help="Creates the environment at prefix/name instead of the default conda location.",
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

    yml_path = WHEELS_DIR.parent / "_environment.yml"
    with open(yml_path, "w") as f:
        yaml.dump(env, f)
    print(f"Temporary environment file created at: {yml_path}")


if __name__ == "__main__":
    args = parse_args()
    write_env_yml(args.env_name)
