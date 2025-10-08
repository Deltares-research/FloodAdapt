from pathlib import Path

import pytest

from flood_adapt.adapter.docker import (
    HAS_DOCKER,
    DockerContainer,
    FiatContainer,
    SfincsContainer,
)


@pytest.mark.parametrize("container_class", [FiatContainer, SfincsContainer])
@pytest.mark.skipif(not HAS_DOCKER, reason="Docker is not available")
class TestDockerContainer:
    @pytest.fixture
    def container(self, tmp_path, container_class):
        c = container_class(root_dir=tmp_path)

        yield c

        c.stop()

    def test_start_creates_container(self, container: DockerContainer):
        assert not container._is_running()
        container.start()
        assert container._is_running()

    def test_start_when_already_running_raises(self, container: DockerContainer):
        container.start()
        assert container._is_running()

        with pytest.raises(RuntimeError):
            container.start()

    def test_stop_stops_container(self, container: DockerContainer):
        container.start()
        assert container._is_running()

        container.stop()
        assert not container._is_running()

    def test_is_running_returns_false_when_not_running(
        self, container: DockerContainer
    ):
        assert not container._is_running()

    def test_is_running_returns_true_when_running(self, container: DockerContainer):
        container.start()
        assert container._is_running()

    def test_run_raises_on_relative_path(self, container: DockerContainer):
        container.start()

        relative_path = Path("relative/path")
        with pytest.raises(ValueError):
            container.run(relative_path)

    def test_run_raises_if_scn_dir_not_within_root(
        self, container: DockerContainer, tmp_path
    ):
        container.start()

        external_path = Path("/tmp")
        if tmp_path in external_path.parents:
            pytest.skip("Environment path conflict")

        with pytest.raises(ValueError):
            container.run(external_path)

    @pytest.mark.skip(reason="TODO integration test: should be tested somehow")
    def test_run_executes_command_successfully(
        self, container: DockerContainer, tmp_path
    ):
        container.start()

        # Create scenario directory
        scn_dir = tmp_path / "scenario"
        scn_dir.mkdir()

        log_path = scn_dir / f"{container.name}.log"

        result = container.run(scn_dir)
        assert result is True
        assert log_path.exists()

        container.stop()
