import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

import pytest
from pydantic import ValidationError

from flood_adapt.config.config import Settings
from flood_adapt.misc.utils import modified_environ

DEFAULT_EXE_PATHS = {
    "windows": {
        "sfincs": Path("win-64/sfincs/sfincs.exe"),
        "fiat": Path("win-64/fiat/fiat.exe"),
    },
    "linux": {
        "sfincs": Path("linux-64/sfincs/bin/sfincs"),
        "fiat": Path("linux-64/fiat/fiat"),
    },
}


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
def dummy_db(tmp_path: Path) -> Callable[..., tuple[Path, str]]:
    def _create(system: str = "windows", name: str = "test") -> tuple[Path, str]:
        system = system.lower()
        root = tmp_path

        for exe in DEFAULT_EXE_PATHS[system].values():
            path = root / "system" / exe
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch(mode=0o755)

        (root / name / "input").mkdir(parents=True)
        (root / name / "static").mkdir(parents=True)
        return root, name

    return _create


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
def mock_subprocess_run(monkeypatch):
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


class TestSettings:
    def assert_settings(
        self,
        settings: Settings,
        root: Path,
        name: str,
        sfincs: Optional[Path] = None,
        fiat: Optional[Path] = None,
    ):
        assert settings.database_root == root
        assert settings.database_name == name
        assert settings.database_path == root / name
        if sfincs is not None:
            assert settings.sfincs_bin_path == sfincs
        if fiat is not None:
            assert settings.fiat_bin_path == fiat

    @pytest.mark.parametrize("system", ["windows", "linux"])
    def test_init_from_args(self, system, dummy_db):
        root, name = dummy_db(system)
        s = Settings(DATABASE_ROOT=root, DATABASE_NAME=name)
        self.assert_settings(s, root, name)

    def test_env_used_when_args_missing(self, dummy_db):
        root, name = dummy_db()
        with modified_environ(DATABASE_ROOT=str(root), DATABASE_NAME=name):
            s = Settings()
        self.assert_settings(s, root, name)

    def test_args_override_env(self, dummy_db):
        root, name = dummy_db()
        with modified_environ(DATABASE_ROOT="wrong", DATABASE_NAME="wrong"):
            s = Settings(DATABASE_ROOT=root, DATABASE_NAME=name)
        self.assert_settings(s, root, name)

    def test_default_db_name_is_first_non_system_dir(self, tmp_path):
        root = tmp_path
        (root / "system").mkdir()
        (root / "b_site" / "input").mkdir(parents=True)
        (root / "b_site" / "static").mkdir()
        (root / "a_site" / "input").mkdir(parents=True)
        (root / "a_site" / "static").mkdir()

        s = Settings(DATABASE_ROOT=root)
        assert s.database_name in {"a_site", "b_site"}
        assert s.database_path.exists()

    def test_invalid_root_raises(self):
        with pytest.raises(ValidationError, match="does not exist"):
            Settings(DATABASE_ROOT=Path("nope"), DATABASE_NAME="x")

    def test_invalid_db_name_raises(self, dummy_db):
        root, _ = dummy_db()
        with pytest.raises(ValidationError, match="does not exist"):
            Settings(DATABASE_ROOT=root, DATABASE_NAME="missing")

    def test_missing_input_folder_raises(self, tmp_path):
        root = tmp_path
        (root / "site" / "static").mkdir(parents=True)
        with pytest.raises(ValidationError, match="input folder"):
            Settings(DATABASE_ROOT=root, DATABASE_NAME="site")

    def test_missing_static_folder_raises(self, tmp_path):
        root = tmp_path
        (root / "site" / "input").mkdir(parents=True)
        with pytest.raises(ValidationError, match="static folder"):
            Settings(DATABASE_ROOT=root, DATABASE_NAME="site")

    def test_missing_sfincs_binary_raises(self, dummy_db):
        root, name = dummy_db()
        with pytest.raises(ValidationError, match="SFINCS binary"):
            Settings(
                DATABASE_ROOT=root,
                DATABASE_NAME=name,
                USE_BINARIES=True,
            )

    def test_missing_fiat_binary_raises(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        sfincs, _ = fake_binaries
        mock_subprocess_run()
        with pytest.raises(ValidationError, match="FIAT binary"):
            Settings(
                DATABASE_ROOT=root,
                DATABASE_NAME=name,
                SFINCS_BIN_PATH=sfincs,
                FIAT_BIN_PATH=None,
                USE_BINARIES=True,
            )

    def test_binary_validation_is_idempotent(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run()
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )

        assert not Settings._binaries_validated
        s.check_binary_versions()
        assert Settings._binaries_validated

    def test_export_to_env_roundtrip(self, dummy_db):
        r1, n1 = dummy_db(name="a")
        r2, n2 = dummy_db(name="b")

        with modified_environ(DATABASE_ROOT=str(r1), DATABASE_NAME=n1):
            s1 = Settings()
            s2 = Settings(DATABASE_ROOT=r2, DATABASE_NAME=n2)
            s2.export_to_env()
            s3 = Settings()

        assert s1 != s2
        assert s3 == s2

    def test_false_booleans_not_persisted(self, dummy_db):
        root, name = dummy_db()
        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            DELETE_CRASHED_RUNS=False,
            VALIDATE_ALLOWED_FORCINGS=False,
            USE_BINARIES=False,
        )
        s.export_to_env()

        assert os.getenv("DELETE_CRASHED_RUNS") is None
        assert os.getenv("VALIDATE_ALLOWED_FORCINGS") is None
        assert os.getenv("USE_BINARIES") is None

    def test_true_booleans_persisted(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run()
        sfincs, fiat = fake_binaries
        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            DELETE_CRASHED_RUNS=True,
            VALIDATE_ALLOWED_FORCINGS=True,
            USE_BINARIES=True,
        )
        s.export_to_env()

        assert os.getenv("DELETE_CRASHED_RUNS") == "True"
        assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "True"
        assert os.getenv("USE_BINARIES") == "True"

    def test_get_sfincs_version_success(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run()
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        assert s.get_sfincs_version() == "v2.2.1-alpha col d'Eze"

    def test_get_sfincs_version_no_match_regex(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run(sfincs_output="some other output without a version")
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        with pytest.raises(ValueError, match=r"version mismatch"):
            s.get_sfincs_version()

    def test_get_fiat_version_success(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run()
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        assert s.get_fiat_version() == "0.2.1"

    def test_get_fiat_version_no_match_regex(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run(fiat_output="some other output without a version")
        sfincs, fiat = fake_binaries
        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        with pytest.raises(ValueError, match=r"version mismatch"):
            s.get_fiat_version()

    def test_check_binary_versions_invalid_sfincs(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run(sfincs_output="invalid sfincs version output")
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        with pytest.raises(ValueError, match=r"SFINCS version mismatch"):
            s.check_binary_versions()

    def test_check_binary_versions_invalid_fiat(
        self, dummy_db, fake_binaries, mock_subprocess_run
    ):
        root, name = dummy_db()
        mock_subprocess_run(fiat_output="invalid fiat version output")
        sfincs, fiat = fake_binaries

        s = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs,
            FIAT_BIN_PATH=fiat,
            USE_BINARIES=True,
        )
        with pytest.raises(ValueError, match=r"FIAT version mismatch"):
            s.check_binary_versions()
