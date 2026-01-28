import os
from pathlib import Path
from typing import Callable, Optional

import pytest
from pydantic import ValidationError

from flood_adapt.config.config import ExecutionMethod, Settings
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
        sfincs_bin.touch(mode=0o755)  # Make executable

        _fiat_rel = DEFAULT_EXE_PATHS[system.lower()]["fiat"]
        fiat_bin = db_root / "system" / _fiat_rel
        fiat_bin.parent.mkdir(parents=True)
        fiat_bin.touch(mode=0o755)  # Make executable

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
        assert os.environ["DATABASE_ROOT"] == expected_root.as_posix()

        assert settings.database_name == expected_name
        assert os.environ["DATABASE_NAME"] == expected_name

        assert settings.database_path == expected_root / expected_name

        if expected_sfincs is not None:
            assert settings.sfincs_bin_path == expected_sfincs
            assert os.environ["SFINCS_BIN_PATH"] == expected_sfincs.as_posix()

        if expected_fiat is not None:
            assert settings.fiat_bin_path == expected_fiat
            assert os.environ["FIAT_BIN_PATH"] == expected_fiat.as_posix()

    @pytest.fixture(autouse=True)
    def protect_and_clear_envvars(self):
        """Create a copy of the environment variables before each test and restore them after.

        After creating the copy, all FA-related environment variables are cleared to ensure tests run in a clean state.
        """
        FA_ENV_VARS = {
            v.alias: os.getenv(v.alias)
            for v in Settings.model_fields.values()
            if v.alias is not None
        }
        try:
            for var in FA_ENV_VARS:
                os.environ.pop(var, None)
            yield
        finally:
            for k, v in FA_ENV_VARS.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.putenv(k, v)

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
            DATABASE_ROOT=db_root.as_posix(),
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
            DATABASE_ROOT=(db_root / "dummy").as_posix(),
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
    def test_missing_model_binaries_raise_validation_error(
        self, system: str, create_dummy_db
    ):
        db_root, name = create_dummy_db(system=system)
        non_existent_path = Path("doesnt_exist")
        with pytest.raises(
            ValidationError, match=f"binary {non_existent_path} does not exist."
        ):
            Settings(
                DATABASE_ROOT=db_root,
                DATABASE_NAME=name,
                FIAT_BIN_PATH=non_existent_path,
                SFINCS_BIN_PATH=non_existent_path,
                VALIDATE_BINARIES=True,
            )

    def test_read_settings_no_envvars(self, create_dummy_db):
        # Arrange
        db_root, name = create_dummy_db()

        config_path = db_root / "config.toml"
        config_path.write_text(
            f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root.as_posix()}'\n"
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
                f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root.as_posix()}'\n"
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
            DATABASE_ROOT=db_root.as_posix(),
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
            DATABASE_ROOT=db_root1.as_posix(),
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
                MANUAL_DOCKER_CONTAINERS=False,
                USE_DOCKER=False,
            )

            assert not settings.delete_crashed_runs
            assert not settings.validate_allowed_forcings
            assert not settings.validate_binaries
            assert not settings.manual_docker_containers
            assert not settings.use_docker
            assert os.getenv("DELETE_CRASHED_RUNS") == "False"
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "False"
            assert os.getenv("VALIDATE_BINARIES") == "False"
            assert os.getenv("MANUAL_DOCKER_CONTAINERS") == "False"
            assert os.getenv("USE_DOCKER") == "False"

            settings2 = Settings()
            assert not settings2.delete_crashed_runs
            assert not settings2.validate_allowed_forcings
            assert not settings2.validate_binaries
            assert not settings2.manual_docker_containers
            assert not settings2.use_docker
            assert os.getenv("DELETE_CRASHED_RUNS") == "False"
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "False"
            assert os.getenv("VALIDATE_BINARIES") == "False"
            assert os.getenv("MANUAL_DOCKER_CONTAINERS") == "False"
            assert os.getenv("USE_DOCKER") == "False"

    def test_create_settings_with_persistent_booleans_true(self):
        with modified_environ():
            settings = Settings(
                DELETE_CRASHED_RUNS=True,
                VALIDATE_ALLOWED_FORCINGS=True,
                MANUAL_DOCKER_CONTAINERS=True,
                USE_DOCKER=True,
            )

            assert settings.delete_crashed_runs
            assert settings.validate_allowed_forcings
            assert settings.manual_docker_containers
            assert settings.use_docker
            assert os.getenv("DELETE_CRASHED_RUNS") == "True"
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "True"
            assert os.getenv("MANUAL_DOCKER_CONTAINERS") == "True"
            assert os.getenv("USE_DOCKER") == "True"

            settings2 = Settings()
            assert settings2.delete_crashed_runs
            assert settings2.validate_allowed_forcings
            assert settings2.manual_docker_containers
            assert settings2.use_docker
            assert os.getenv("DELETE_CRASHED_RUNS") == "True"
            assert os.getenv("VALIDATE_ALLOWED_FORCINGS") == "True"
            assert os.getenv("MANUAL_DOCKER_CONTAINERS") == "True"
            assert os.getenv("USE_DOCKER") == "True"

    def test_get_scenario_execution_method_docker(self):
        settings = Settings(
            USE_DOCKER=True,
            VALIDATE_BINARIES=False,
            SFINCS_BIN_PATH=None,
            FIAT_BIN_PATH=None,
        )
        assert settings.get_scenario_execution_method() == ExecutionMethod.DOCKER

    def test_get_scenario_execution_method_binaries(self, tmp_path: Path):
        existing_bin = tmp_path / "bins/binary.exe"
        existing_bin.parent.mkdir(parents=True, exist_ok=True)
        existing_bin.touch(mode=0o755)  # Make executable

        settings = Settings(
            USE_DOCKER=False,
            VALIDATE_BINARIES=True,
            SFINCS_BIN_PATH=existing_bin,
            FIAT_BIN_PATH=existing_bin,
        )
        assert settings.get_scenario_execution_method() == ExecutionMethod.BINARIES

    def test_get_scenario_execution_method_none(self, tmp_path: Path):
        settings = Settings(
            USE_DOCKER=False,
            VALIDATE_BINARIES=False,
            SFINCS_BIN_PATH=None,
            FIAT_BIN_PATH=None,
        )
        assert settings.get_scenario_execution_method() is None

    def test_get_scenario_execution_method_strict_raises(self, tmp_path: Path):
        settings = Settings(
            USE_DOCKER=False,
            VALIDATE_BINARIES=False,
            SFINCS_BIN_PATH=None,
            FIAT_BIN_PATH=None,
        )
        with pytest.raises(
            RuntimeError,
            match="Could not determine scenario execution method, please check your configuration.",
        ):
            settings.get_scenario_execution_method(strict=True)

    def test_get_scenario_execution_method_all_available_chooses_binaries(
        self, tmp_path: Path
    ):
        existing_bin = tmp_path / "bins/binary.exe"
        existing_bin.parent.mkdir(parents=True, exist_ok=True)
        existing_bin.touch(mode=0o755)  # Make executable

        settings = Settings(
            USE_DOCKER=True,
            VALIDATE_BINARIES=True,
            SFINCS_BIN_PATH=existing_bin,
            FIAT_BIN_PATH=existing_bin,
        )
        assert settings.get_scenario_execution_method() == ExecutionMethod.BINARIES
