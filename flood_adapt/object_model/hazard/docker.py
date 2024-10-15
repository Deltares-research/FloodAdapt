import subprocess
from pathlib import Path
import os


def run_sfincs_in_docker(input_directory: Path) -> bool:
    """
    Run the SFINCS model in a Docker container.

    Parameters
    ----------
    input_directory : Path
        Path to the input directory to be mounted in the Docker container.

    Returns
    -------
    bool
        True if the Sfincs run executed successfully, False otherwise.

    Raises
    ------
    ValueError
        If the specified input directory does not exist.
    """

    if not input_directory.is_dir():
        raise ValueError(f"The specified directory does not exist: {input_directory}")
    
    docker_command = [
        "docker", "run", "--rm",
        "-v", f"{input_directory}:/data",  # Mount the input directory to /data
        "deltares/sfincs-cpu:latest"       # Docker image
    ]

    try:
        result = subprocess.run(docker_command, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return False
