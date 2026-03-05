import logging
import re
import subprocess
from abc import ABC
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    subprocess.run(
        ["docker", "--version"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    HAS_DOCKER = True
except Exception:
    HAS_DOCKER = False


class DockerContainer(ABC):
    CONTAINERS_INITIALIZED: int = 0

    def __init__(
        self,
        name: str,
        container_image: str,
        command: list[str],
    ):
        self.container_image = container_image  # Docker image name on Docker Hub
        self.name = name  # Name to assign to the container
        self._command = command  # Command to run inside the container
        self._mount_dir = "/data/flood_adapt"  # Directory inside the container
        self._root_dir: Path | None = None  # Host directory the container has access to
        self._container_created = False

    def start(self, root_dir: Path) -> None:
        """Start the Docker container by giving it access to root_dir.

        Parameters
        ----------
        root_dir : Path
            Absolute path to directory on host machine to mount inside container.

        Raises
        ------
        RuntimeError
            If the container fails to start.
        """
        if self._container_created:
            logger.info(f"Container {self.name} is already running.")
            return

        root_dir = root_dir.resolve()
        logger.info(f"Starting container {self.name} from {self.container_image}...")
        docker_command = [
            "docker",
            "run",
            "-d",
            "--name",
            self.name,
            "-v",
            f"{root_dir.as_posix()}:{self._mount_dir}",
            "-w",
            self._mount_dir,
            "--entrypoint",
            "/bin/sh",
            self.container_image,
            "-c",
            "tail -f /dev/null",
        ]

        process = subprocess.run(
            docker_command,
            text=True,
            capture_output=True,
        )
        if process.returncode != 0:
            msg = (
                f"Docker run failed with code {process.returncode}. "
                f"Failed to start container `{self.name}`. Command was: {' '.join(docker_command)}. "
                f"stdout:\n{process.stdout}. "
                f"stderr:\n{process.stderr}. "
            )
            logger.error(
                msg
                + "Attempting to stop any existing container with the same name and retrying... "
            )
            self._force_remove_container()
            retry = subprocess.run(
                docker_command,
                text=True,
                capture_output=True,
            )
            if retry.returncode != 0:
                msg += (
                    f"Retry also failed with code {retry.returncode}. "
                    f"retry stdout:\n{retry.stdout}. "
                    f"retry stderr:\n{retry.stderr}. "
                )
                logger.error(msg)
                raise RuntimeError(msg)

        self._root_dir = root_dir
        self._container_created = True
        DockerContainer.CONTAINERS_INITIALIZED += 1

    def stop(self) -> None:
        if self._is_running():
            logger.info(f"Stopping container `{self.name}`...")
            subprocess.run(["docker", "stop", self.name], check=True)
            subprocess.run(["docker", "rm", self.name], check=True)
        self._root_dir = None
        self._container_created = False

    def run(self, scn_dir: Path) -> bool:
        """
        Run the container in a given scenario directory relative to root_dir.

        Parameters
        ----------
        scn_dir : Path
            Absolute path where simulation should run.
        """
        if not self._container_created or self._root_dir is None:
            raise RuntimeError(
                "Container is not started. Call `container.start(root_dir)` first."
            )
        if not scn_dir.is_absolute():
            raise ValueError(f"scn_dir: {scn_dir} must be an absolute path")
        if self._root_dir not in scn_dir.parents and self._root_dir != scn_dir:
            raise ValueError(
                f"scn_dir: {scn_dir} must be within root_dir: {self._root_dir}"
            )

        log_file = scn_dir / f"{self.name}.log"
        relative_cwd = scn_dir.relative_to(self._root_dir)

        return self._exec(
            cwd=relative_cwd,
            log_file=log_file,
        )

    def _exec(self, cwd: Path, log_file: Path) -> bool:
        if not self._container_created or self._root_dir is None:
            raise RuntimeError(
                "Container is not started. Call `container.start(root_dir)` first."
            )

        cwd_inside = f"{self._mount_dir}/{cwd.as_posix()}"
        docker_command = [
            "docker",
            "exec",
            "-w",
            cwd_inside,
            self.name,
        ] + self._command

        logger.info(f"Exec Docker: {' '.join(docker_command)}")

        with open(log_file, "w") as log_handler:
            process = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
            )
            log_handler.write(process.stdout)
            log_handler.write(process.stderr)

        if process.returncode != 0:
            logger.error(
                f"Docker exec failed (code {process.returncode}). See {log_file}"
            )
            logger.error(f"Command was: {' '.join(docker_command)}")
        return process.returncode == 0

    def _is_running(self) -> bool:
        """Return True if the container exists and is running."""
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Running}}",
                self.name,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:  # container does not exist / docker not installed
            return False

        if result.stdout is not None:  # should be "true" or "false"
            return result.stdout.strip().lower() == "true"

        return False  # fallback, should not happen

    def _force_remove_container(self) -> None:
        subprocess.run(
            ["docker", "rm", "-f", self.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


class SfincsContainer(DockerContainer):
    def __init__(self, version: str = "latest"):
        """Initialize a python wrapper for a Docker container for SFINCS execution.

        Parameters
        ----------
        version : str
            Version of SFINCS to use. Should be a str with a sub str in the format "x.y.z" or "latest".
            The version is used to pull the correct Docker image.
        """
        super().__init__(
            name="sfincs",
            container_image=f"deltares/sfincs-cpu:{_get_docker_tag_for_sfincs_version(version)}",
            command=["sfincs"],
        )


class FiatContainer(DockerContainer):
    def __init__(self, version: str = "latest"):
        """Initialize a python wrapper for a Docker container for FIAT execution.

        Parameters
        ----------
        version : str
            Version of FIAT to use. Should be a str with a sub str in the format "x.y.z" or "latest".
            The version is used to pull the correct Docker image.
        """
        super().__init__(
            name="fiat",
            container_image=f"deltares/fiat:{_get_docker_tag_for_fiat_version(version)}",
            command=[
                "pixi",
                "run",
                "--frozen",
                "--manifest-path",
                "/home/deltares/pixi.toml",
                "-e",
                "default",
                "fiat",
                "run",
                "settings.toml",
            ],
        )


# Mapping from SFINCS version to Docker image tag, based on the available tags at https://hub.docker.com/r/deltares/sfincs-cpu/tags
SFINCS_BIN_VERSION_TO_DOCKER_TAG: dict[str, str] = {
    "latest": "latest",
    "2.3.0": "sfincs-v2.3.0-mt-Faber-Release",
    "2.2.0": "sfincs-v2.2.0-col-dEze-Release",
    "2.2.1": "sfincs-v2.2.0-col-dEze-Release",
    "2.1.1": "sfincs-v2.1.1-Dollerup-Release",
}

# Mapping from FIAT version to Docker image tag, based on the available tags at https://hub.docker.com/r/deltares/fiat/tags
FIAT_BIN_VERSION_TO_DOCKER_TAG: dict[str, str] = {
    "latest": "latest",
    "0.2.1": "v0.2.1",
}


def _get_docker_tag_for_sfincs_version(sfincs_version: str) -> str:
    normalized = _normalize_sfincs_version(sfincs_version)
    if normalized in SFINCS_BIN_VERSION_TO_DOCKER_TAG:
        return SFINCS_BIN_VERSION_TO_DOCKER_TAG[normalized]
    else:
        raise ValueError(
            f"No Docker image found for SFINCS version {sfincs_version}. ({normalized}) "
            f"Supported versions are: {list(SFINCS_BIN_VERSION_TO_DOCKER_TAG)}"
        )


def _get_docker_tag_for_fiat_version(fiat_version: str) -> str:
    normalized = _normalize_fiat_version(fiat_version)
    if normalized in FIAT_BIN_VERSION_TO_DOCKER_TAG:
        return FIAT_BIN_VERSION_TO_DOCKER_TAG[normalized]
    else:
        raise ValueError(
            f"No Docker image found for FIAT version {fiat_version}. ({normalized}) "
            f"Supported versions are: {list(FIAT_BIN_VERSION_TO_DOCKER_TAG.keys())}"
        )


def _normalize_sfincs_version(version: str) -> str:
    version = version.strip()
    if version == "latest":
        return "latest"

    match = re.search(r"(\d+\.\d+\.\d+)", version)
    if not match:
        raise ValueError(f"Could not parse SFINCS version from '{version}'")

    return match.group(1)


def _normalize_fiat_version(version: str) -> str:
    version = version.strip()
    if version == "latest":
        return "latest"

    match = re.search(r"(\d+\.\d+\.\d+)", version)
    if not match:
        raise ValueError(f"Could not parse FIAT version from '{version}'")

    return match.group(1)
