from pathlib import Path
import subprocess
from pathlib import Path
import os
import logging
import sys
from flood_adapt.log import FloodAdaptLogging

logger = FloodAdaptLogging.getLogger("SfincsAdapter")

def execute_sfincs(simulation_dir: Path) -> bool:
    logger.info(
        f"Running SFINCS model for {'-'.join(simulation_dir.parts[-2:])}."
    )
    if sys.platform == "win32":
        run_success = _run_sfincs_win(simulation_dir)
    elif sys.platform == "linux":
        run_success = _run_sfincs_linux(simulation_dir)
    else:
        raise ValueError(f"Unsupported platform: {sys.platform}")
    return run_success

def _run_sfincs_win(simulation_dir: Path) -> bool:
    with cd(simulation_dir):
        with open("sfincs.log", "w") as log_handler:
            try:
                process = subprocess.run(
                    Settings().sfincs_path.as_posix(),check=True, text=True, stdout=log_handler
                )
            except subprocess.CalledProcessError as e:
                if process.stderr:
                    logger.error(process.stderr)
    logger.info(f"Finished evaluating SFINCS simulation: {simulation_dir}")
    return process.returncode == 0


def _run_sfincs_linux(simulation_dir: Path) -> bool:
    """
    Run the SFINCS model in a Docker container.

    Parameters
    ----------
    simulation_dir : Path
        Path to the simulation directory to be mounted in the Docker container.

    Returns
    -------
    bool
        True if the Sfincs run executed successfully, False otherwise.

    Raises
    ------
    ValueError
        If the specified input directory does not exist.
    """

    if not simulation_dir.is_dir():
        raise ValueError(f"The specified directory does not exist: {simulation_dir}")

    docker_command = [
        "docker", "run", "--rm",
        "-v", f"{simulation_dir}:/data",  # Mount the input directory to /data
        "deltares/sfincs-cpu:latest"       # Docker image
    ]
    log_file = simulation_dir / "sfincs.log"

    with open(log_file, "w") as log_handler:
        try:
            process = subprocess.run(docker_command, check=True, text=True, stdout=log_handler)
        except subprocess.CalledProcessError as e:
            if process.stderr:
                logger.error(process.stderr)
    logger.info(f"Finished evaluating SFINCS simulation: {simulation_dir}")
    return process.returncode == 0

