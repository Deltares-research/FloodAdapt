import os
import subprocess
import sys
from pathlib import Path

from flood_adapt.config import Settings
from flood_adapt.log import FloodAdaptLogging
from flood_adapt.object_model.utils import cd

logger = FloodAdaptLogging.getLogger("FiatAdapter")


def execute_fiat(simulation_dir: Path) -> bool:
    logger.info(f"Running FIAT model for {'-'.join(simulation_dir.parts[-2:])}.")
    if sys.platform == "win32":
        run_success = _run_fiat_win(simulation_dir)
    elif sys.platform == "linux":
        run_success = _run_fiat_linux(simulation_dir)
    else:
        raise ValueError(f"Unsupported platform: {sys.platform}")
    logger.info(
        f"{'SUCCESS' if run_success else 'FAILED'} - finished evaluation of FIAT simulation: {simulation_dir}"
    )
    return run_success


def _run_fiat_win(simulation_dir: Path) -> bool:
    with cd(simulation_dir):
        with open(simulation_dir / "fiat.log", "a") as log_handler:
            process = subprocess.run(
                f'"{Settings().fiat_path.as_posix()}" run settings.toml',
                stdout=log_handler,
                stderr=log_handler,
                env=os.environ.copy(),  # need environment variables from runtime hooks
                check=True,
                shell=True,
            )
    return process.returncode == 0


def _run_fiat_linux(simulation_dir: Path) -> bool:
    """
    Run the FIAT model in a Docker container.

    Parameters
    ----------
    simulation_dir : Path
        The directory containing all the input files for the FIAT model.
        Path to the simulation directory to be mounted in the Docker container.
        
    Returns
    -------
    bool
        True if the Fiat run executed successfully, False otherwise.

    Raises
    ------
    ValueError
        If the specified input directory does not exist.
    """
    if not simulation_dir.is_dir():
        raise ValueError(f"The specified directory does not exist: {simulation_dir}")

    docker_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{simulation_dir}:/home/deltares/data",  # Mount the input directory to /home/deltares
        "fiat",  # Docker image
        "fiat run /home/deltares/data/settings.toml", # Run command
    ]
    
    log_file = simulation_dir / "fiat.log"

    with open(log_file, "w") as log_handler:
        process = subprocess.run(docker_command, text=True, stdout=log_handler)
        if process.stderr:
            logger.error(process.stderr)
    return process.returncode == 0
