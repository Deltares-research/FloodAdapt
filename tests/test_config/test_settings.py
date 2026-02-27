import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Generator

import pytest
from pydantic import ValidationError

from flood_adapt.config.settings import Settings
from flood_adapt.misc.utils import modified_environ


@pytest.fixture(autouse=True)
def isolated_settings_env(monkeypatch):
    env_backup = {
        f.alias: os.getenv(f.alias) for f in Settings.model_fields.values() if f.alias
    }

    for key in env_backup:
        monkeypatch.delenv(key, raising=False)

    Settings._binaries_validated = False
    yield

    for key, value in env_backup.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    Settings._binaries_validated = False


@pytest.fixture
def fake_binaries(tmp_path: Path) -> tuple[Path, Path]:
    def make(name: str) -> Path:
        if sys.platform == "win32":
            name += ".exe"
        path = tmp_path / name
        path.touch(mode=0o755)
        return path

    return make("sfincs"), make("fiat")


@pytest.fixture
def mock_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Callable[..., None], Any, None]:
    expected_sfincs_output = (
        "------------ Welcome to SFINCS ------------\n"
        "\n"
        "Build-Revision: $Rev: v2.2.1-alpha col d'Eze\n"
        "Build-Date: $Date: 2025-06-02\n"
    )
    expected_fiat_output = "FIAT 0.2.1, build 2025-02-24T16:19:19 UTC+0100\n"
    orig_run = subprocess.run

    def _mocker(
        sfincs_output: str = expected_sfincs_output,
        fiat_output: str = expected_fiat_output,
    ):
        class FakeResult:
            def __init__(self, out):
                self.stdout = out

        def fake_run(cmd, *args, **kwargs):
            exe_name_no_suffix = Path(cmd[0]).stem
            if exe_name_no_suffix == "sfincs":
                return FakeResult(sfincs_output)
            if exe_name_no_suffix == "fiat":
                return FakeResult(fiat_output)
            raise RuntimeError(f"Unexpected subprocess call: {cmd}")

        monkeypatch.setattr(subprocess, "run", fake_run)

    yield _mocker

    subprocess.run = orig_run


def test_init_from_args(tmp_path: Path):
    name = "test"
    (tmp_path / name / "input").mkdir(parents=True)
    (tmp_path / name / "static").mkdir(parents=True)
    s = Settings(DATABASE_ROOT=tmp_path, DATABASE_NAME=name)
    assert s.database_root == tmp_path
    assert s.database_name == name
    assert s.database_path == tmp_path / name


def test_env_used_when_args_missing(tmp_path: Path):
    name = "test"
    (tmp_path / name / "input").mkdir(parents=True)
    (tmp_path / name / "static").mkdir(parents=True)
    with modified_environ(DATABASE_ROOT=str(tmp_path), DATABASE_NAME=name):
        s = Settings()
    assert s.database_root == tmp_path
    assert s.database_name == name
    assert s.database_path == tmp_path / name


def test_args_override_env(tmp_path: Path):
    name = "test"
    (tmp_path / name / "input").mkdir(parents=True)
    (tmp_path / name / "static").mkdir(parents=True)
    with modified_environ(DATABASE_ROOT="wrong", DATABASE_NAME="wrong"):
        s = Settings(DATABASE_ROOT=tmp_path, DATABASE_NAME=name)
    assert s.database_root == tmp_path
    assert s.database_name == name
    assert s.database_path == tmp_path / name


def test_invalid_root_raises():
    with pytest.raises(ValidationError, match="is not a directory"):
        Settings(DATABASE_ROOT=Path("not-a-directory"), DATABASE_NAME="x")


def test_invalid_db_name_raises(tmp_path: Path):
    with pytest.raises(ValidationError, match=r"Database .* at .* does not exist\."):
        Settings(DATABASE_ROOT=tmp_path, DATABASE_NAME="missing")


def test_missing_input_folder_raises(tmp_path: Path):
    name = "test"
    (tmp_path / name / "static").mkdir(parents=True)
    with pytest.raises(ValidationError, match="input folder"):
        Settings(DATABASE_ROOT=tmp_path, DATABASE_NAME=name)


def test_missing_static_folder_raises(tmp_path: Path):
    name = "test"
    (tmp_path / name / "input").mkdir(parents=True)
    with pytest.raises(ValidationError, match="static folder"):
        Settings(DATABASE_ROOT=tmp_path, DATABASE_NAME=name)


def test_missing_sfincs_binary_raises(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    with pytest.raises(ValidationError, match="SFINCS binary path is not set."):
        Settings(
            USE_BINARIES=True,
            SFINCS_BIN_PATH=None,
            FIAT_BIN_PATH=fake_binaries[1],
        )


def test_missing_fiat_binary_raises(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    with pytest.raises(ValidationError, match="FIAT binary path is not set."):
        Settings(
            SFINCS_BIN_PATH=fake_binaries[0],
            FIAT_BIN_PATH=None,
            USE_BINARIES=True,
        )


def test_binary_validation_is_idempotent(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )

    assert not Settings._binaries_validated
    s.check_binary_versions()
    assert Settings._binaries_validated


def test_export_to_env_roundtrip(tmp_path: Path):
    root1, name1 = tmp_path, "test1"
    root2, name2 = tmp_path, "test2"
    (tmp_path / name1 / "input").mkdir(parents=True)
    (tmp_path / name1 / "static").mkdir(parents=True)
    (tmp_path / name2 / "input").mkdir(parents=True)
    (tmp_path / name2 / "static").mkdir(parents=True)

    with modified_environ(DATABASE_ROOT=str(root1), DATABASE_NAME=name1):
        s1 = Settings()
        s2 = Settings(DATABASE_ROOT=root2, DATABASE_NAME=name2)
        s2.export_to_env()
        s3 = Settings()

    assert s1 != s2
    assert s3 == s2


def test_false_booleans_persisted():
    Settings(
        DELETE_CRASHED_RUNS=False,
        VALIDATE_ALLOWED_FORCINGS=False,
        USE_BINARIES=False,
    ).export_to_env()

    s = Settings()
    assert os.getenv("DELETE_CRASHED_RUNS") == "False"
    assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "False"
    assert os.getenv("USE_BINARIES") == "False"
    assert s.delete_crashed_runs is False
    assert s.validate_allowed_forcings is False
    assert s.use_binaries is False


def test_true_booleans_persisted(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    sfincs, fiat = fake_binaries
    Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        DELETE_CRASHED_RUNS=True,
        VALIDATE_ALLOWED_FORCINGS=True,
        USE_BINARIES=True,
    ).export_to_env()

    s = Settings()
    assert os.getenv("DELETE_CRASHED_RUNS") == "True"
    assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "True"
    assert os.getenv("USE_BINARIES") == "True"
    assert s.delete_crashed_runs is True
    assert s.validate_allowed_forcings is True
    assert s.use_binaries is True


def test_get_sfincs_version_success(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    assert s.get_sfincs_version() == "2.2.1-alpha col d'Eze"


def test_get_sfincs_version_no_match_regex(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run(sfincs_output="some other output without a version")
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    with pytest.raises(ValueError, match=r"version mismatch"):
        s.get_sfincs_version()


def test_get_fiat_version_success(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run()
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    assert s.get_fiat_version() == "0.2.1"


def test_get_fiat_version_no_match_regex(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run(fiat_output="some other output without a version")
    sfincs, fiat = fake_binaries
    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    with pytest.raises(ValueError, match=r"version mismatch"):
        s.get_fiat_version()


def test_check_binary_versions_invalid_sfincs(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run(sfincs_output="invalid sfincs version output")
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    with pytest.raises(ValueError, match=r"SFINCS version mismatch"):
        s.check_binary_versions()


def test_check_binary_versions_invalid_fiat(
    fake_binaries: tuple[Path, Path],
    mock_subprocess_run: Callable[..., None],
):
    mock_subprocess_run(fiat_output="invalid fiat version output")
    sfincs, fiat = fake_binaries

    s = Settings(
        SFINCS_BIN_PATH=sfincs,
        FIAT_BIN_PATH=fiat,
        USE_BINARIES=True,
    )
    with pytest.raises(ValueError, match=r"FIAT version mismatch"):
        s.check_binary_versions()


def test_database_path_raises_when_not_set():
    s = Settings()
    with pytest.raises(ValueError, match=r"database_root or database_name is not set"):
        _ = s.database_path
