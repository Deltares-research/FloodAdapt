import logging
import subprocess
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


class DockerContainerManager:
    def __init__(self, container_image: str, root_dir: Path):
        self.container_image = container_image
        self.root_dir = root_dir.resolve()
        self.container_name = (
            f"{container_image.replace('/', '_')}_{uuid.uuid4().hex[:8]}"
        )
        self._running = False

    def start(self) -> None:
        if self._running:
            raise RuntimeError("Container is already running")
        logger.info(
            f"Starting container {self.container_name} from {self.container_image}…"
        )
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",  # remove after stop
                "-d",  # detached
                "--name",  # container name
                self.container_name,
                "-v",  # volume
                f"{self.root_dir.as_posix()}:/data",  # mount root_dir to /data
                "-w",  # working directory
                "/data",  # start in /data
                self.container_image,
                "sleep",
                "infinity",  # keep container running
            ],
            check=True,
        )
        self._running = True

    def stop(self) -> None:
        if self._running:
            logger.info(f"Stopping container {self.container_name}…")
            subprocess.run(["docker", "stop", self.container_name], check=True)
            self._running = False

    def exec(self, command: list[str], cwd: Path, log_file: Path) -> bool:
        if not self._running:
            raise RuntimeError("Container is not running")

        cwd_inside = f"/data/{cwd.as_posix()}"
        docker_command = [
            "docker",
            "exec",
            "-w",
            cwd_inside,
            self.container_name,
        ] + command

        logger.info(f"Exec Docker: {' '.join(docker_command)}")

        with open(log_file, "w") as log_handler:
            process = subprocess.run(
                docker_command, stdout=log_handler, stderr=subprocess.STDOUT, text=True
            )

        if process.returncode != 0:
            logger.error(
                f"Docker exec failed (code {process.returncode}). See {log_file}"
            )
        return process.returncode == 0


class SfincsContainer(DockerContainerManager):
    def __init__(self, root_dir: Path):
        super().__init__("deltares/sfincs-cpu:latest", root_dir)

    def run(self, scn_dir: Path) -> bool:
        """
        Run Sfincs in a given scenario directory relative to root_dir.

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

        log_file = scn_dir / "sfincs.log"
        relative_cwd = scn_dir.relative_to(self.root_dir)

        return self.exec(
            command=[],  # Sfincs runs default command
            cwd=relative_cwd,  # container's cwd relative to mounted root
            log_file=log_file,
        )


class FiatContainer(DockerContainerManager):
    def __init__(self, root_dir: Path):
        super().__init__("deltares/fiat:latest", root_dir)

    def run(self, scn_dir: Path) -> bool:
        """
        Run Fiat in a given scenario directory relative to root_dir.

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

        log_file = scn_dir / "fiat.log"
        relative_cwd = scn_dir.relative_to(self.root_dir)

        return self.exec(
            command=["fiat", "run", "settings.toml"],
            cwd=relative_cwd,  # container cwd
            log_file=log_file,
        )


def start_containers(
    database_root: Path,
) -> tuple[SfincsContainer, FiatContainer]:
    sfincs_container = SfincsContainer(database_root)
    sfincs_container.start()

    fiat_container = FiatContainer(database_root)
    fiat_container.start()

    return sfincs_container, fiat_container
