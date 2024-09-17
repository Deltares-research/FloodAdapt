import os
import shutil
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from flood_adapt.config import Settings
from tests.utils import cleared_envvars, modified_environ


class TestSettingsModel:
    def _create_dummy_db(self, db_root: Path, name: str, system: str) -> Path:
        ext = Settings.SYSTEM_SUFFIXES[system]

        (db_root / "system" / "sfincs").mkdir(parents=True)
        fd = os.open(db_root / "system" / "sfincs" / f"sfincs{ext}", os.O_CREAT)
        os.close(fd)

        (db_root / "system" / "fiat").mkdir(parents=True)
        fd = os.open(db_root / "system" / "fiat" / f"fiat{ext}", os.O_CREAT)
        os.close(fd)

        (db_root / name / "input").mkdir(parents=True)
        (db_root / name / "static").mkdir(parents=True)
        return db_root

    def _assert_settings(
        self,
        settings: Settings,
        system: str,
        expected_name: Optional[str] = None,
        expected_root: Optional[Path] = None,
        expected_system_folder: Optional[Path] = None,
    ):
        expected_ext = Settings.SYSTEM_SUFFIXES[system]

        if expected_root is None:
            expected_root = Path(Settings.model_fields["database_root"].default)

        if expected_system_folder is None:
            expected_system_folder = expected_root / "system"

        if expected_name is None:
            sites = [
                d
                for d in os.listdir(expected_root)
                if d != "system" and not d.startswith(".")
            ]
            if not sites:
                raise ValueError(f"No databases found in {expected_root}.")
            expected_name = sites[0]

        assert settings.database_root == expected_root
        assert settings.database_name == expected_name
        assert settings.database_path == expected_root / expected_name
        assert settings.system_folder == expected_system_folder
        assert (
            settings.sfincs_path
            == expected_system_folder / "sfincs" / f"sfincs{expected_ext}"
        )
        assert (
            settings.fiat_path
            == expected_system_folder / "fiat" / f"fiat{expected_ext}"
        )

        assert os.environ["DATABASE_ROOT"] == str(expected_root)
        assert os.environ["DATABASE_NAME"] == expected_name
        assert os.environ["SYSTEM_FOLDER"] == str(expected_system_folder)

    @pytest.fixture()
    def mock_system(self):
        with patch("flood_adapt.config.system") as mock_system:
            yield mock_system

    @pytest.fixture(autouse=True, scope="class")
    def protect_external_settings(self):
        settings = Settings()

        yield

        Settings(
            database_root=settings.database_root,
            database_name=settings.database_name,
            system_folder=settings.system_folder,
        )

    @pytest.fixture(autouse=True)
    def protect_envvars(self):
        root = os.environ.get("DATABASE_ROOT", None)
        name = os.environ.get("DATABASE_NAME", None)
        system_folder = os.environ.get("SYSTEM_FOLDER", None)

        yield

        if root is not None:
            os.environ["DATABASE_ROOT"] = root
        if name is not None:
            os.environ["DATABASE_NAME"] = name
        if system_folder is not None:
            os.environ["SYSTEM_FOLDER"] = system_folder

    @pytest.fixture()
    def clear_envvars(self):
        with cleared_envvars("DATABASE_ROOT", "DATABASE_NAME", "SYSTEM_FOLDER"):
            yield

    @pytest.mark.skip(
        reason="TODO: Add sfincs & fiat binaries for Linux & Darwin to the system folder in the test database"
    )
    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_defaults_no_envvars(
        self, system: str, mock_system, clear_envvars
    ):
        # Arrange
        mock_system.return_value = system

        # Act
        settings = Settings()

        # Assert
        self._assert_settings(settings, system)

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_args_no_envvars(
        self, system: str, tmp_path: Path, mock_system, clear_envvars
    ):
        # Arrange
        mock_system.return_value = system
        name = "test_name"
        db_root = self._create_dummy_db(tmp_path, name, system)

        # Act
        settings = Settings(
            database_root=db_root,
            database_name=name,
            system_folder=db_root / "system",
        )

        # Assert
        self._assert_settings(
            settings,
            system,
            expected_name=name,
            expected_root=db_root,
            expected_system_folder=db_root / "system",
        )

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_envvars_overwriting_defaults(
        self, system: str, tmp_path: Path, mock_system
    ):
        # Arrange
        mock_system.return_value = system
        name = "test_name"

        with modified_environ(
            DATABASE_ROOT=str(tmp_path),
            DATABASE_NAME=name,
            SYSTEM_FOLDER=str(tmp_path / "system"),
        ):
            db_root = self._create_dummy_db(tmp_path, name, system)

            # Act
            settings = Settings()

            # Assert
            self._assert_settings(
                settings,
                system,
                expected_name=name,
                expected_root=db_root,
            )

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_args_overwriting_envvars(
        self, system: str, tmp_path: Path, mock_system
    ):
        # Arrange
        mock_system.return_value = system
        name = "test_name"
        db_root = self._create_dummy_db(tmp_path, name, system)

        with modified_environ(
            DATABASE_ROOT=str(tmp_path / "dummy"),
            DATABASE_NAME="invalid_name",
            SYSTEM_FOLDER=str(tmp_path / "dummy_system"),
        ):
            # Act
            settings = Settings(
                database_root=db_root,
                database_name=name,
                system_folder=db_root / "system",
            )

            # Assert
            self._assert_settings(
                settings,
                system,
                expected_name=name,
                expected_root=db_root,
                expected_system_folder=db_root / "system",
            )

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_args_different_system_folder(
        self, system: str, tmp_path: Path, mock_system, clear_envvars
    ):
        # Arrange
        mock_system.return_value = system
        name = "test_name"
        db_root = self._create_dummy_db(tmp_path, name, system)
        new_system_path = db_root / "another_system_folder"
        shutil.copytree(db_root / "system", new_system_path)
        shutil.rmtree(db_root / "system")

        # Act
        settings = Settings(
            database_root=db_root,
            database_name=name,
            system_folder=new_system_path,
        )

        # Assert
        self._assert_settings(
            settings,
            system,
            expected_name=name,
            expected_root=db_root,
            expected_system_folder=new_system_path,
        )

    def test_init_from_invalid_db_root_raise_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            Settings(database_name="test", database_root=Path("invalid"))

        assert "Database root invalid does not exist." in str(exc_info.value)

    def test_init_from_invalid_db_name_raise_validation_error(self):
        name = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            Settings(database_name=name)

        assert f"Database name {name} does not exist" in str(exc_info.value)

    def test_init_from_invalid_system_folder_raise_validation_error(
        self, tmp_path: Path
    ):
        name = "test_name"
        db_root = self._create_dummy_db(tmp_path, name, "Windows")
        dummy_system_folder = db_root / "dummy"

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                database_root=db_root,
                database_name=name,
                system_folder=dummy_system_folder,
            )

        assert f"System folder {dummy_system_folder} does not exist." in str(
            exc_info.value
        )

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    @pytest.mark.parametrize("model", ["fiat", "sfincs"])
    def test_missing_model_binaries_raise_validation_error(
        self, system: str, model: str, tmp_path: Path, mock_system
    ):
        name = "test_name"
        mock_system.return_value = system
        db_root = self._create_dummy_db(tmp_path, name, system)
        model_bin = (
            db_root / "system" / model / f"{model}{Settings.SYSTEM_SUFFIXES[system]}"
        )
        os.remove(model_bin)

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                database_root=db_root,
                database_name=name,
                system_folder=db_root / "system",
            )

        assert f"{model.upper()} binary {model_bin} does not exist." in str(
            exc_info.value
        )

    def test_invalid_os_raise_validation_error(self, mock_system):
        mock_system.return_value = "invalid"
        with pytest.raises(ValueError) as exc_info:
            _ = Settings()
        assert "Unsupported system " in str(exc_info.value)

    def test_read_settings_no_envvars(self, tmp_path: Path, mock_system, clear_envvars):
        # Arrange
        mock_system.return_value = "Windows"
        name = "new_name"
        db_root = self._create_dummy_db(tmp_path, name, "Windows")

        config_path = tmp_path / "config.toml"
        config_path.write_text(
            f"database_name = '{name}'\ndatabase_root = '{db_root}'\nsystem_folder = '{db_root / 'system'}'\n"
        )

        # Act
        settings = Settings.read(config_path)

        # Assert
        self._assert_settings(
            settings,
            "Windows",
            expected_root=db_root,
            expected_name=name,
            expected_system_folder=db_root / "system",
        )

    def test_read_settings_overwrites_envvars(self, tmp_path: Path, mock_system):
        # Arrange
        mock_system.return_value = "Windows"
        name = "new_name"

        with modified_environ(
            DATABASE_ROOT="dummy_root",
            DATABASE_NAME="dummy_name",
            SYSTEM_FOLDER="dummy_system",
        ):
            db_root = self._create_dummy_db(tmp_path, name, "Windows")

            config_path = tmp_path / "config.toml"
            config_path.write_text(
                f"database_name = '{name}'\ndatabase_root = '{db_root}'\nsystem_folder = '{db_root / 'system'}'\n"
            )

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings,
                "Windows",
                expected_root=db_root,
                expected_name=name,
                expected_system_folder=db_root / "system",
            )

    def test_read_settings_missing_fields_filled_by_envvars(
        self, tmp_path: Path, mock_system
    ):
        # Arrange
        mock_system.return_value = "Windows"
        name = "new_name"
        db_root = self._create_dummy_db(tmp_path, name, "Windows")

        with modified_environ(
            DATABASE_ROOT=str(db_root),
            DATABASE_NAME="dummy_name",
            SYSTEM_FOLDER=str(db_root / "system"),
        ):
            config_path = tmp_path / "config.toml"
            config_path.write_text(f"database_name = '{name}'\n")

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings,
                "Windows",
                expected_root=db_root,
                expected_name=name,
                expected_system_folder=db_root / "system",
            )

    def test_creating_settings_object_changes_envvars(
        self, tmp_path: Path, mock_system
    ):
        # Arrange
        name1 = "old_name"
        name2 = "new_name"
        db_root1 = self._create_dummy_db(tmp_path / "old", name1, "Windows")
        db_root2 = self._create_dummy_db(tmp_path / "new", name2, "Windows")
        system = "Windows"
        mock_system.return_value = system

        # Act
        with modified_environ(
            DATABASE_ROOT=str(db_root1),
            DATABASE_NAME=name1,
            SYSTEM_FOLDER=str(db_root1 / "system"),
        ):
            from_env1 = Settings()  # Create settings object with envvars
            from_args = Settings(  # Create settings object with new values and check if envvars are updated
                database_name=name2,
                database_root=db_root2,
                system_folder=db_root2 / "system",
            )

            from_env2 = Settings()  # Create settings object with updated envvars again

            # Assert
            self._assert_settings(
                from_args,
                system,
                expected_name=name2,
                expected_root=db_root2,
                expected_system_folder=db_root2 / "system",
            )

            assert from_env1 != from_args
            assert from_env1 != from_env2
            assert from_env2 == from_args
