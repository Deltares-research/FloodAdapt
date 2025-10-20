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


@pytest.mark.parametrize("container_class", [FiatContainer, SfincsContainer])
@pytest.mark.skipif(not HAS_DOCKER, reason="Docker is not available")
class TestDockerContainer:
    @pytest.fixture(scope="class", autouse=True)
    def pause_containers(self):
        """Stop all session scoped running containers for the duration of the class tests, then restart them afterward."""
        SFINCS_CONTAINER.stop()
        FIAT_CONTAINER.stop()

        yield

        SFINCS_CONTAINER.start()
        FIAT_CONTAINER.start()

    @pytest.fixture
    def running_container(self, tmp_path: Path, container_class):
        c = container_class(root_dir=tmp_path)
        c.start()
        yield c
        c.stop()

    @pytest.fixture
    def container(self, tmp_path: Path, container_class):
        yield container_class(root_dir=tmp_path)

    def test_start_and_stop(self, container: DockerContainer):
        assert not container._is_running()
        container.start()
        assert container._is_running()
        container.stop()
        assert not container._is_running()

    def test_is_running_returns_false_when_not_running(
        self, container: DockerContainer
    ):
        assert not container._is_running()

    def test_start_when_already_running_warns(
        self, running_container: DockerContainer, caplog: pytest.LogCaptureFixture
    ):
        with caplog.at_level(logging.INFO):
            running_container.start()

        assert "is already running" in caplog.text

    def test_is_running_returns_true_when_running(
        self, running_container: DockerContainer
    ):
        assert running_container._is_running()

    def test_run_raises_on_relative_path(self, running_container: DockerContainer):
        relative_path = Path("relative/path")
        with pytest.raises(ValueError):
            running_container.run(relative_path)

    def test_run_raises_if_root_dir_is_None(self, running_container: DockerContainer):
        running_container.root_dir = None
        with pytest.raises(ValueError):
            running_container.run(Path("some/path"))

    def test_run_raises_if_external_path(self, running_container: DockerContainer):
        assert running_container.root_dir is not None
        external_path = running_container.root_dir.parent / "external_scn"
        external_path.mkdir(parents=True, exist_ok=True)

        with pytest.raises(ValueError):
            running_container.run(external_path)

    @pytest.mark.skip(reason="TODO integration test: should be tested somehow")
    def test_run_executes_command_successfully(
        self, running_container: DockerContainer, tmp_path
    ):
        # Create scenario directory
        scn_dir = tmp_path / "scenario"
        scn_dir.mkdir()

        log_path = scn_dir / f"{running_container.name}.log"

        result = running_container.run(scn_dir)
        assert result is True
        assert log_path.exists()
