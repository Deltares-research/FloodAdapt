import logging
from pathlib import Path

import pytest

from flood_adapt.adapter.docker import (
    FIAT_CONTAINER,
    HAS_DOCKER,
    SFINCS_CONTAINER,
    DockerContainer,
    FiatContainer,
    SfincsContainer,
)
from flood_adapt.config.config import Settings


@pytest.mark.parametrize("container_class", [FiatContainer, SfincsContainer])
@pytest.mark.skipif(not HAS_DOCKER, reason="Docker is not available")
class TestDockerContainer:
    @pytest.fixture(scope="class", autouse=True)
    def pause_containers(self, setup_settings: Settings):
        """Stop all session scoped running containers for the duration of the class tests, then restart them afterward."""
        SFINCS_CONTAINER.stop()
        FIAT_CONTAINER.stop()

        yield

        SFINCS_CONTAINER.start(setup_settings.database_path)
        FIAT_CONTAINER.start(setup_settings.database_path)

    @pytest.fixture
    def running_container(
        self, tmp_path: Path, container_class: type[FiatContainer | SfincsContainer]
    ):
        c = container_class()
        c.start(root_dir=tmp_path)
        yield c
        c.stop()

    @pytest.fixture
    def container(self, container_class: type[FiatContainer | SfincsContainer]):
        yield container_class()

    def test_start_and_stop(
        self,
        container: DockerContainer,
        tmp_path: Path,
    ):
        assert not container._is_running()
        container.start(root_dir=tmp_path)
        assert container._is_running()
        container.stop()
        assert not container._is_running()

    def test_start_when_already_running_warns(
        self, running_container: DockerContainer, caplog: pytest.LogCaptureFixture
    ):
        assert running_container._root_dir is not None
        with caplog.at_level(logging.INFO):
            running_container.start(running_container._root_dir)

        assert "is already running" in caplog.text

    def test_is_running_returns_false_when_not_running(
        self, container: DockerContainer
    ):
        assert not container._is_running()

    def test_is_running_returns_true_when_running(
        self, running_container: DockerContainer
    ):
        assert running_container._is_running()

    def test_run_raises_on_relative_path(self, running_container: DockerContainer):
        relative_path = Path("relative/path")
        with pytest.raises(ValueError, match="must be an absolute path"):
            running_container.run(relative_path)

    def test_run_raises_if_root_dir_is_None(self, running_container: DockerContainer):
        running_container._root_dir = None
        with pytest.raises(RuntimeError, match="Container is not started."):
            running_container.run(Path("some/path"))

    def test_run_raises_if_external_path(self, running_container: DockerContainer):
        assert running_container._root_dir is not None
        external_path = running_container._root_dir.parent / "external_scn"
        external_path.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError, match="must be within root_dir"):
            running_container.run(external_path)
