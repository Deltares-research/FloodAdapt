import os
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from flood_adapt.misc.config import SYSTEM_SUFFIXES, Settings
from tests.utils import modified_environ


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
        ext = SYSTEM_SUFFIXES[system]

        sfincs_bin = db_root / "system" / "sfincs" / f"sfincs{ext}"
        sfincs_bin.parent.mkdir(parents=True)
        sfincs_bin.touch()

        fiat_bin = db_root / "system" / "fiat" / f"fiat{ext}"
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
            assert settings.sfincs_path == expected_sfincs
            assert os.environ["SFINCS_BIN_PATH"] == str(expected_sfincs)

        if expected_fiat is not None:
            assert settings.fiat_path == expected_fiat
            assert os.environ["FIAT_BIN_PATH"] == str(expected_fiat)

    @pytest.fixture()
    def mock_system(self):
        with patch("flood_adapt.misc.config.system") as mock_system:
            mock_system.return_value = "Windows"
            yield mock_system

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
    @pytest.mark.parametrize("system", SYSTEM_SUFFIXES.keys())
    def test_init_from_defaults_no_envvars(self, system: str, mock_system):
        # Arrange
        mock_system.return_value = system

        # Act
        settings = Settings()

        # Assert
        self._assert_settings(settings=settings)

    @pytest.mark.parametrize("system", SYSTEM_SUFFIXES.keys())
    def test_init_from_args_no_envvars(self, system: str, create_dummy_db, mock_system):
        # Arrange
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)
        sfincs_bin = db_root / "system" / "sfincs" / f"sfincs{SYSTEM_SUFFIXES[system]}"
        fiat_bin = db_root / "system" / "fiat" / f"fiat{SYSTEM_SUFFIXES[system]}"

        # Act
        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            SFINCS_BIN_PATH=sfincs_bin,
            FIAT_BIN_PATH=fiat_bin,
        )

        # Assert
        self._assert_settings(
            settings=settings,
            expected_name=name,
            expected_root=db_root,
            expected_sfincs=sfincs_bin,
            expected_fiat=fiat_bin,
        )

    @pytest.mark.parametrize("system", SYSTEM_SUFFIXES.keys())
    def test_init_from_envvars_overwriting_defaults(
        self, system: str, create_dummy_db: Callable, mock_system
    ):
        # Arrange
        mock_system.return_value = system
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

    @pytest.mark.parametrize("system", SYSTEM_SUFFIXES.keys())
    def test_init_from_args_overwriting_envvars(
        self, system: str, create_dummy_db, mock_system
    ):
        # Arrange
        mock_system.return_value = system
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

    @pytest.mark.parametrize("system", SYSTEM_SUFFIXES.keys())
    @pytest.mark.parametrize("model", ["fiat", "sfincs"])
    def test_missing_model_binaries_raise_validation_error(
        self, system: str, model: str, create_dummy_db, mock_system
    ):
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)
        non_existent_path = Path("doesnt_exist")
        with pytest.raises(ValidationError) as exc_info:
            if model == "fiat":
                Settings(
                    DATABASE_ROOT=db_root,
                    DATABASE_NAME=name,
                    FIAT_BIN_PATH=non_existent_path,
                )
            elif model == "sfincs":
                Settings(
                    DATABASE_ROOT=db_root,
                    DATABASE_NAME=name,
                    SFINCS_BIN_PATH=non_existent_path,
                )
            else:
                raise ValueError("Invalid model")

        assert f"{model.upper()} binary {non_existent_path} does not exist." in str(
            exc_info.value
        )

    def test_read_settings_no_envvars(self, create_dummy_db, mock_system):
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

    def test_read_settings_overwrites_envvars(self, create_dummy_db, mock_system):
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

    def test_read_settings_missing_fields_filled_by_envvars(
        self, create_dummy_db, mock_system
    ):
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

    def test_creating_settings_object_changes_envvars(
        self, create_dummy_db, mock_system
    ):
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
