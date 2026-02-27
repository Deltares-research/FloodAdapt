import logging
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
    def __init__(self, version_tag: str = "latest"):
        super().__init__(
            name="sfincs",
            container_image=f"deltares/sfincs-cpu:{version_tag}",
            command=["sfincs"],
        )


class FiatContainer(DockerContainer):
    def __init__(self, version_tag: str = "latest"):
        super().__init__(
            name="fiat",
            container_image=f"deltares/fiat:{version_tag}",
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
