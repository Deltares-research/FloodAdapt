import logging
import re
import subprocess
import uuid
from abc import ABC
from pathlib import Path

logger = logging.getLogger(__name__)

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


class DockerContainer(ABC):
    def __init__(
        self, name: str, container_image: str, root_dir: Path, command: list[str]
    ):
        self.container_image = container_image
        self.root_dir = root_dir.resolve()
        self.container_name = self._sanitize_container_name(container_image)
        self.name = name
        self._command = command
        self._mount_dir = "/data/flood_adapt"

    def start(self) -> None:
        if self._is_running():
            raise RuntimeError(f"Container {self.container_name} is already running")
        logger.info(
            f"Starting container {self.container_name} from {self.container_image}…"
        )
        docker_command = [
            "docker",
            "run",
            "-d",
            "--name",
            self.container_name,
            "-v",
            f"{self.root_dir.as_posix()}:{self._mount_dir}",
            "-w",
            self._mount_dir,
            "--entrypoint",
            "/bin/sh",
            self.container_image,
            "-c",
            "tail -f /dev/null",
        ]

        subprocess.run(
            docker_command,
            check=True,
        )

        if not self._is_running():
            raise RuntimeError(
                f"Failed to start container: `{self.container_name}` from image `{self.container_image}`."
            )

    def stop(self) -> None:
        if self._is_running():
            logger.info(f"Stopping container `{self.container_name}`...")
            subprocess.run(["docker", "stop", self.container_name], check=True)
            subprocess.run(["docker", "rm", self.container_name], check=True)

    def run(self, scn_dir: Path) -> bool:
        """
        Run the container in a given scenario directory relative to root_dir.

        Parameters
        ----------
        scn_dir : Path
            Absolute path where simulation should run.
        """
        if not scn_dir.is_absolute():
            raise ValueError(f"scn_dir: {scn_dir} must be an absolute path")

        if self.root_dir not in scn_dir.parents and self.root_dir != scn_dir:
            raise ValueError(
                f"scn_dir: {scn_dir} must be within root_dir: {self.root_dir}"
            )

        if not self._is_running():
            logger.warning(
                f"Expected container {self.container_name} to be running. (Re)starting it anyways."
            )
            self.start()

        log_file = scn_dir / f"{self.name}.log"
        relative_cwd = scn_dir.relative_to(self.root_dir)

        return self._exec(
            cwd=relative_cwd,
            log_file=log_file,
        )

    def _exec(self, cwd: Path, log_file: Path) -> bool:
        if not self._is_running():
            raise RuntimeError("Container is not running")

        cwd_inside = f"{self._mount_dir}/{cwd.as_posix()}"
        docker_command = [
            "docker",
            "exec",
            "-w",
            cwd_inside,
            self.container_name,
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
                self.container_name,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:  # container does not exist
            return False

        if result.stdout is not None:  # should be "true" or "false"
            return result.stdout.strip().lower() == "true"

        return False  # fallback, should not happen

    def _sanitize_container_name(
        self, image_name: str, include_hex: bool = True
    ) -> str:
        name = re.sub(r"[^a-zA-Z0-9_.-]", "_", image_name)
        if include_hex:
            name += f"_{uuid.uuid4().hex[:8]}"
        return name


class SfincsContainer(DockerContainer):
    def __init__(self, root_dir: Path):
        super().__init__(
            name="sfincs",
            container_image="deltares/sfincs-cpu:latest",
            root_dir=root_dir,
            command=["sfincs"],
        )


class FiatContainer(DockerContainer):
    def __init__(self, root_dir: Path):
        super().__init__(
            name="fiat",
            container_image="deltares/fiat:latest",
            root_dir=root_dir,
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
