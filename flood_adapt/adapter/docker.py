import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["run_sfincs", "run_fiat", "HAS_DOCKER"]


try:
    subprocess.run(
        ["docker", "info"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    HAS_DOCKER = True
except Exception:
    HAS_DOCKER = False


def _run_docker(
    container_image: str, mount_dir: Path, command: list[str], log_file: Path
) -> bool:
    """Run a command inside a Docker container with logging.

    Parameters
    ----------
    container_image : str
        Docker image to run.
    mount_dir : Path
        Directory to mount in the container.
    command : list[str]
        Command to run inside the container.
    log_file : Path
        File to log stdout and stderr.

    Returns
    -------
    bool
        True if the container exited with code 0.
    """
    if not mount_dir.is_dir():
        raise ValueError(f"The specified directory does not exist: {mount_dir}")

    mount_dir_posix = mount_dir.resolve().as_posix()
    docker_command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{mount_dir_posix}:/data",
        container_image,
    ] + command

    logger.info(f"Running Docker: {' '.join(docker_command)}")

    with open(log_file, "w") as log_handler:
        process = subprocess.run(
            docker_command, stdout=log_handler, stderr=subprocess.STDOUT, text=True
        )

    if process.returncode != 0:
        logger.error(
            f"Docker process failed with return code {process.returncode}. See {log_file}"
        )
    return process.returncode == 0


def run_sfincs(simulation_dir: Path) -> bool:
    log_file = simulation_dir / "sfincs.log"
    return _run_docker(
        container_image="deltares/sfincs-cpu:latest",
        mount_dir=simulation_dir,
        command=[],  # Sfincs container runs the main executable by default
        log_file=log_file,
    )


def run_fiat(simulation_dir: Path) -> bool:
    log_file = simulation_dir / "fiat.log"
    return _run_docker(
        container_image="deltares/fiat:latest",
        mount_dir=simulation_dir,
        command=["fiat", "run", "/data/settings.toml"],
        log_file=log_file,
    )
