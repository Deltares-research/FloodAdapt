import os
import subprocess
from pathlib import Path
from typing import Callable, Optional

import pytest
from pydantic import ValidationError

from flood_adapt.config.config import Settings
from flood_adapt.misc.utils import modified_environ

DEFAULT_EXE_PATHS: dict[str, dict[str, Path]] = {
    "windows": {
        "sfincs": Path("win-64/sfincs/sfincs.exe"),
        "fiat": Path("win-64/fiat/fiat.exe"),
    },
    "linux": {
        "sfincs": Path("linux-64/sfincs/bin/sfincs"),
        "fiat": Path("linux-64/fiat/fiat"),
    },
}


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    expected_sfincs_output = (
        "------------ Welcome to SFINCS ------------\n"
        "\n"
        "Build-Revision: $Rev: v2.2.1-alpha col d'Eze\n"
        "Build-Date: $Date: 2025-06-02\n"
    )
    expected_fiat_output = "FIAT 0.2.1, build 2025-02-24T16:19:19 UTC+0100\n"

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

    return _mocker


class TestSettingsModel:
    @pytest.fixture
    def create_dummy_db(
        self, tmp_path: Path
    ) -> Callable[[Path, str, str], tuple[Path, str]]:
        def _create_dummy_db(
            db_root: Path = tmp_path, name: str = "test", system: str = "Windows"
        ) -> tuple[Path, str]:
            if db_root != tmp_path:
                db_root = tmp_path / db_root
            return self._create_dummy_db(db_root, name, system)

        return _create_dummy_db

    def _create_dummy_db(
        self, db_root: Path, name: str = "test", system: str = "Windows"
    ) -> tuple[Path, str]:
        sfincs_rel = DEFAULT_EXE_PATHS[system.lower()]["sfincs"]
        sfincs_bin = db_root / "system" / sfincs_rel
        sfincs_bin.parent.mkdir(parents=True)
        sfincs_bin.touch()

        _fiat_rel = DEFAULT_EXE_PATHS[system.lower()]["fiat"]
        fiat_bin = db_root / "system" / _fiat_rel
        fiat_bin.parent.mkdir(parents=True)
        fiat_bin.touch()

        (db_root / name / "input").mkdir(parents=True)
        (db_root / name / "static").mkdir(parents=True)
        return db_root, name

    def _assert_settings(
        self,
        settings: Settings,
        expected_root: Path = Path(Settings.model_fields["database_root"].default),
        expected_name: str = "charleston_test",
        expected_sfincs: Optional[Path] = None,
        expected_fiat: Optional[Path] = None,
    ):
        assert settings.database_root == expected_root
        assert os.environ["DATABASE_ROOT"] == str(expected_root)

        assert settings.database_name == expected_name
        assert os.environ["DATABASE_NAME"] == expected_name

        assert settings.database_path == expected_root / expected_name

        if expected_sfincs is not None:
            assert settings.sfincs_bin_path == expected_sfincs
            assert os.environ["SFINCS_BIN_PATH"] == str(expected_sfincs)

        if expected_fiat is not None:
            assert settings.fiat_bin_path == expected_fiat
            assert os.environ["FIAT_BIN_PATH"] == str(expected_fiat)

    @pytest.fixture(autouse=True, scope="class")
    def protect_external_settings(self):
        settings = Settings()

        yield

        Settings(
            DATABASE_ROOT=settings.database_root,
            DATABASE_NAME=settings.database_name,
        )

    @pytest.fixture(autouse=True)
    def protect_envvars(self):
        root = os.environ.get("DATABASE_ROOT", None)
        name = os.environ.get("DATABASE_NAME", None)
        sfincs_bin = os.environ.get("SFINCS_BIN_PATH", None)
        fiat_bin = os.environ.get("FIAT_BIN_PATH", None)

        with modified_environ(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs_bin,
            FIAT_BIN_PATH=fiat_bin,
        ):
            yield

    @pytest.mark.skip(
        reason="TODO: Add sfincs & fiat binaries for Linux & Darwin to the system folder in the test database"
    )
    @pytest.mark.parametrize("system", ["windows", "linux"])
    def test_init_from_defaults_no_envvars(self, system: str):
        # Arrange
        # Act
        settings = Settings()

        # Assert
        self._assert_settings(settings=settings)

    @pytest.mark.parametrize("system", ["windows", "linux"])
    def test_init_from_args_no_envvars(self, system: str, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db(system=system)

        # Act
        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
        )

        # Assert
        self._assert_settings(
            settings=settings,
            expected_name=name,
            expected_root=db_root,
        )

    @pytest.mark.parametrize("system", ["windows", "linux"])
    def test_init_from_envvars_overwriting_defaults(
        self, system: str, create_dummy_db: Callable
    ):
        # Arrange
        db_root, name = create_dummy_db(system=system)

        with modified_environ(
            DATABASE_ROOT=str(db_root),
            DATABASE_NAME=name,
        ):
            # Act
            settings = Settings()

            # Assert
            self._assert_settings(
                settings=settings,
                expected_name=name,
                expected_root=db_root,
            )

    @pytest.mark.parametrize("system", ["windows", "linux"])
    def test_init_from_args_overwriting_envvars(self, system: str, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db(system=system)

        with modified_environ(
            DATABASE_ROOT=str(db_root / "dummy"),
            DATABASE_NAME="invalid_name",
        ):
            # Act
            settings = Settings(
                DATABASE_ROOT=db_root,
                DATABASE_NAME=name,
            )

            # Assert
            self._assert_settings(
                settings=settings,
                expected_name=name,
                expected_root=db_root,
            )

    def test_init_from_invalid_db_root_raise_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_NAME="test", DATABASE_ROOT=Path("invalid"))

        assert "Database root invalid does not exist." in str(exc_info.value)

    def test_init_from_invalid_db_name_raise_validation_error(self):
        name = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_NAME=name)

        assert f"Database {name} at" in str(exc_info.value)
        assert "does not exist." in str(exc_info.value)

    @pytest.mark.parametrize("system", ["windows", "linux"])
    @pytest.mark.parametrize("model", ["fiat", "sfincs"])
    def test_missing_model_binaries_raise_validation_error(
        self, system: str, model: str, create_dummy_db
    ):
        db_root, name = create_dummy_db(system=system)
        non_existent_path = Path("doesnt_exist")
        with pytest.raises(ValidationError) as exc_info:
            if model == "fiat":
                Settings(
                    DATABASE_ROOT=db_root,
                    DATABASE_NAME=name,
                    FIAT_BIN_PATH=non_existent_path,
                    VALIDATE_BINARIES=True,
                )
            elif model == "sfincs":
                Settings(
                    DATABASE_ROOT=db_root,
                    DATABASE_NAME=name,
                    SFINCS_BIN_PATH=non_existent_path,
                    VALIDATE_BINARIES=True,
                )
            else:
                raise ValueError("Invalid model")

        assert f"{model.upper()} binary {non_existent_path} does not exist." in str(
            exc_info.value
        )

    def test_read_settings_no_envvars(self, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db()

        config_path = db_root / "config.toml"
        config_path.write_text(
            f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root}'\n"
        )

        # Act
        settings = Settings.read(config_path)

        # Assert
        self._assert_settings(
            settings=settings,
            expected_root=db_root,
            expected_name=name,
        )

    def test_read_settings_overwrites_envvars(self, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db()

        with modified_environ(
            DATABASE_ROOT="dummy_root",
            DATABASE_NAME="dummy_name",
        ):
            config_path = db_root / "config.toml"
            config_path.write_text(
                f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root}'\n"
            )

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings=settings,
                expected_root=db_root,
                expected_name=name,
            )

    def test_read_settings_missing_fields_filled_by_envvars(self, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db()

        with modified_environ(
            DATABASE_ROOT=str(db_root),
            DATABASE_NAME="dummy_name",
        ):
            config_path = db_root / "config.toml"
            config_path.write_text(f"DATABASE_NAME = '{name}'\n")

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings=settings,
                expected_root=db_root,
                expected_name=name,
            )

    def test_creating_settings_object_changes_envvars(self, create_dummy_db):
        # Arrange
        db_root1, name1 = create_dummy_db("root1", "name1")
        db_root2, name2 = create_dummy_db("root2", "name2")

        # Act
        with modified_environ(
            DATABASE_ROOT=str(db_root1),
            DATABASE_NAME=name1,
        ):
            from_env1 = Settings()  # Create settings object with envvars
            from_args = Settings(  # Create settings object with new values and check if envvars are updated
                DATABASE_NAME=name2,
                DATABASE_ROOT=db_root2,
            )

            from_env2 = Settings()  # Create settings object with updated envvars again

            # Assert
            self._assert_settings(
                settings=from_args,
                expected_name=name2,
                expected_root=db_root2,
            )

            assert from_env1 != from_args
            assert from_env1 != from_env2
            assert from_env2 == from_args

    def test_create_settings_with_persistent_booleans_false(self):
        # Arrange
        with modified_environ():
            settings = Settings(
                DELETE_CRASHED_RUNS=False,
                VALIDATE_ALLOWED_FORCINGS=False,
                VALIDATE_BINARIES=False,
            )

            assert not settings.delete_crashed_runs
            assert not settings.validate_allowed_forcings
            assert not settings.validate_binaries
            assert not os.getenv("DELETE_CRASHED_RUNS")
            assert not os.getenv("VALIDATE_ALLOWED_FORCINGS")
            assert not os.getenv("VALIDATE_BINARIES")

            settings2 = Settings()
            assert not settings2.delete_crashed_runs
            assert not settings2.validate_allowed_forcings
            assert not settings2.validate_binaries
            assert not os.getenv("DELETE_CRASHED_RUNS")
            assert not os.getenv("VALIDATE_ALLOWED_FORCINGS")
            assert not os.getenv("VALIDATE_BINARIES")

    def test_create_settings_with_persistent_booleans_true(self):
        with modified_environ():
            settings = Settings(
                DELETE_CRASHED_RUNS=True,
                VALIDATE_ALLOWED_FORCINGS=True,
                VALIDATE_BINARIES=True,
            )

            assert settings.delete_crashed_runs
            assert settings.validate_allowed_forcings
            assert settings.validate_binaries
            assert os.getenv("DELETE_CRASHED_RUNS")
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS")
            assert os.getenv("VALIDATE_BINARIES")

            settings2 = Settings()
            assert settings2.delete_crashed_runs
            assert settings2.validate_allowed_forcings
            assert settings2.validate_binaries
            assert os.getenv("DELETE_CRASHED_RUNS")
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS")
            assert os.getenv("VALIDATE_BINARIES")

    @pytest.fixture
    def fake_sfincs_exe(self, tmp_path: Path) -> Path:
        exe_path = tmp_path / "sfincs.exe"
        exe_path.touch()
        return exe_path

    @pytest.fixture
    def fake_fiat_exe(self, tmp_path: Path) -> Path:
        exe_path = tmp_path / "fiat.exe"
        exe_path.touch()
        return exe_path

    def test_get_sfincs_version_success(
        self,
        create_dummy_db,
        fake_sfincs_exe,
        fake_fiat_exe,
        mock_subprocess_run,
    ):
        # Arrange
        db_root, name = create_dummy_db()
        mock_subprocess_run()

        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=fake_sfincs_exe,
            FIAT_BIN_PATH=fake_fiat_exe,
            VALIDATE_BINARIES=True,
            SFINCS_VERSION="v2.2.1-alpha col d'Eze",
            FIAT_VERSION="0.2.1",
        )

        # Act
        version = settings.get_sfincs_version()

        # Assert
        assert version == "v2.2.1-alpha col d'Eze"

    def test_get_sfincs_version_no_match(
        self,
        create_dummy_db,
        mock_subprocess_run,
    ):
        # Arrange
        db_root, name = create_dummy_db()
        mock_subprocess_run(
            sfincs_output=("some unrelated output\nnothing to match here")
        )

        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            VALIDATE_BINARIES=False,
            SFINCS_VERSION="v2.2.1-alpha col d'Eze",
        )
        with pytest.raises(ValueError, match="Version not found"):
            settings.get_sfincs_version()

    def test_get_sfincs_version_no_path(self, create_dummy_db):
        db_root, name = create_dummy_db()
        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=None,
            VALIDATE_BINARIES=False,
        )

        with pytest.raises(ValueError, match="SFINCS binary path is not set"):
            settings.get_sfincs_version()

    def test_settings_init_raises_on_incorrect_version(
        self,
        create_dummy_db,
        mock_subprocess_run,
        fake_sfincs_exe,
        fake_fiat_exe,
    ):
        root, name = create_dummy_db()
        mock_subprocess_run()

        with pytest.raises(
            ValueError,
            match="Sfincs version mismatch: expected v2.2.10-something, got v2.2.1-alpha col d'Eze.",
        ):
            Settings(
                DATABASE_ROOT=root,
                DATABASE_NAME=name,
                FIAT_BIN_PATH=fake_fiat_exe,
                SFINCS_BIN_PATH=fake_sfincs_exe,
                VALIDATE_BINARIES=True,
                FIAT_VERSION="0.1.1",
                SFINCS_VERSION="v2.2.10-something",  # incorrect version
            )

    def test_get_fiat_version_success(
        self,
        create_dummy_db,
        mock_subprocess_run,
        fake_sfincs_exe,
        fake_fiat_exe,
    ):
        root, name = create_dummy_db()
        mock_subprocess_run()
        settings = Settings(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=fake_sfincs_exe,
            FIAT_BIN_PATH=fake_fiat_exe,
            VALIDATE_BINARIES=True,
            FIAT_VERSION="0.2.1",
            SFINCS_VERSION="v2.2.1-alpha col d'Eze",
        )
        version = settings.get_fiat_version()
        assert version == "0.2.1"

    def test_get_fiat_version_no_pattern(
        self,
        fake_fiat_exe: Path,
        create_dummy_db,
        mock_subprocess_run,
    ):
        mock_subprocess_run(fiat_output="something else\nno version here")
        db_root, name = create_dummy_db()
        settings = Settings(
            FIAT_BIN_PATH=fake_fiat_exe,
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            VALIDATE_BINARIES=False,
        )

        with pytest.raises(ValueError, match="Version not found"):
            settings.get_fiat_version()

    def test_get_fiat_version_no_path(self, create_dummy_db):
        db_root, name = create_dummy_db()

        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            FIAT_BIN_PATH=None,
            VALIDATE_BINARIES=False,
        )

        with pytest.raises(ValueError, match="FIAT binary path is not set"):
            settings.get_fiat_version()
