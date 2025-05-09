import os
import shutil
from pathlib import Path
from typing import Callable, Optional
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from flood_adapt.config.config import Settings
from flood_adapt.misc.utils import modified_environ


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
        ext = Settings.SYSTEM_SUFFIXES[system]

        (db_root / "system" / "sfincs").mkdir(parents=True)
        with open(db_root / "system" / "sfincs" / f"sfincs{ext}", "w"):
            pass

        (db_root / "system" / "fiat").mkdir(parents=True)
        with open(db_root / "system" / "fiat" / f"fiat{ext}", "w"):
            pass

        (db_root / name / "input").mkdir(parents=True)
        (db_root / name / "static").mkdir(parents=True)
        return db_root, name

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
        with patch("flood_adapt.config.config.system") as mock_system:
            mock_system.return_value = "Windows"
            yield mock_system

    @pytest.fixture(autouse=True, scope="class")
    def protect_external_settings(self):
        settings = Settings()

        yield

        Settings(
            DATABASE_ROOT=settings.database_root,
            DATABASE_NAME=settings.database_name,
            SYSTEM_FOLDER=settings.system_folder,
        )

    @pytest.fixture(autouse=True)
    def protect_envvars(self):
        root = os.environ.get("DATABASE_ROOT", None)
        name = os.environ.get("DATABASE_NAME", None)
        system_folder = os.environ.get("SYSTEM_FOLDER", None)

        with modified_environ(
            DATABASE_ROOT=root,
            DATABASE_NAME=name,
            SYSTEM_FOLDER=system_folder,
        ):
            yield

    @pytest.mark.skip(
        reason="TODO: Add sfincs & fiat binaries for Linux & Darwin to the system folder in the test database"
    )
    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_defaults_no_envvars(self, system: str, mock_system):
        # Arrange
        mock_system.return_value = system

        # Act
        settings = Settings()

        # Assert
        self._assert_settings(settings, system)

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    def test_init_from_args_no_envvars(self, system: str, create_dummy_db, mock_system):
        # Arrange
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)

        # Act
        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            SYSTEM_FOLDER=db_root / "system",
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
        self, system: str, create_dummy_db: Callable, mock_system
    ):
        # Arrange
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)

        with modified_environ(
            DATABASE_ROOT=str(db_root),
            DATABASE_NAME=name,
            SYSTEM_FOLDER=str(db_root / "system"),
        ):
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
        self, system: str, create_dummy_db, mock_system
    ):
        # Arrange
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)

        with modified_environ(
            DATABASE_ROOT=str(db_root / "dummy"),
            DATABASE_NAME="invalid_name",
            SYSTEM_FOLDER=str(db_root / "dummy_system"),
        ):
            # Act
            settings = Settings(
                DATABASE_ROOT=db_root,
                DATABASE_NAME=name,
                SYSTEM_FOLDER=db_root / "system",
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
        self, system: str, create_dummy_db, mock_system
    ):
        # Arrange
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)

        new_system_path = db_root / "another_system_folder"
        shutil.copytree(db_root / "system", new_system_path)
        shutil.rmtree(db_root / "system")

        # Act
        settings = Settings(
            DATABASE_ROOT=db_root,
            DATABASE_NAME=name,
            SYSTEM_FOLDER=new_system_path,
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
            Settings(DATABASE_NAME="test", DATABASE_ROOT=Path("invalid"))

        assert "Database root invalid does not exist." in str(exc_info.value)

    def test_init_from_invalid_db_name_raise_validation_error(self):
        name = "invalid"
        with pytest.raises(ValidationError) as exc_info:
            Settings(DATABASE_NAME=name)

        assert f"Database {name} at" in str(exc_info.value)
        assert "does not exist." in str(exc_info.value)

    def test_init_from_invalid_system_folder_raise_validation_error(
        self, create_dummy_db
    ):
        db_root, name = create_dummy_db()
        dummy_system_folder = db_root / "dummy"

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_ROOT=db_root,
                DATABASE_NAME=name,
                SYSTEM_FOLDER=dummy_system_folder,
            )

        assert f"System folder {dummy_system_folder} does not exist." in str(
            exc_info.value
        )

    @pytest.mark.parametrize("system", Settings.SYSTEM_SUFFIXES.keys())
    @pytest.mark.parametrize("model", ["fiat", "sfincs"])
    def test_missing_model_binaries_raise_validation_error(
        self, system: str, model: str, create_dummy_db, mock_system
    ):
        mock_system.return_value = system
        db_root, name = create_dummy_db(system=system)

        model_bin = (
            db_root / "system" / model / f"{model}{Settings.SYSTEM_SUFFIXES[system]}"
        )
        os.remove(model_bin)

        with pytest.raises(ValidationError) as exc_info:
            Settings(
                DATABASE_ROOT=db_root,
                DATABASE_NAME=name,
                SYSTEM_FOLDER=db_root / "system",
            )

        assert f"{model.upper()} binary {model_bin} does not exist." in str(
            exc_info.value
        )

    def test_invalid_os_raise_validation_error(self, mock_system):
        mock_system.return_value = "invalid"
        with pytest.raises(ValueError) as exc_info:
            _ = Settings()
        assert "Unsupported system " in str(exc_info.value)

    def test_read_settings_no_envvars(self, create_dummy_db, mock_system):
        # Arrange
        db_root, name = create_dummy_db()

        config_path = db_root / "config.toml"
        config_path.write_text(
            f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root}'\nSYSTEM_FOLDER = '{db_root / 'system'}'\n"
        )

        # Act
        settings = Settings.read(config_path)

        # Assert
        self._assert_settings(
            settings,
            mock_system(),
            expected_root=db_root,
            expected_name=name,
            expected_system_folder=db_root / "system",
        )

    def test_read_settings_overwrites_envvars(self, create_dummy_db, mock_system):
        # Arrange
        db_root, name = create_dummy_db()

        with modified_environ(
            DATABASE_ROOT="dummy_root",
            DATABASE_NAME="dummy_name",
            SYSTEM_FOLDER="dummy_system",
        ):
            config_path = db_root / "config.toml"
            config_path.write_text(
                f"DATABASE_NAME = '{name}'\nDATABASE_ROOT = '{db_root}'\nSYSTEM_FOLDER = '{db_root / 'system'}'\n"
            )

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings,
                mock_system(),
                expected_root=db_root,
                expected_name=name,
                expected_system_folder=db_root / "system",
            )

    def test_read_settings_missing_fields_filled_by_envvars(
        self, create_dummy_db, mock_system
    ):
        # Arrange
        db_root, name = create_dummy_db()

        with modified_environ(
            DATABASE_ROOT=str(db_root),
            DATABASE_NAME="dummy_name",
            SYSTEM_FOLDER=str(db_root / "system"),
        ):
            config_path = db_root / "config.toml"
            config_path.write_text(f"DATABASE_NAME = '{name}'\n")

            # Act
            settings = Settings.read(config_path)

            # Assert
            self._assert_settings(
                settings,
                mock_system(),
                expected_root=db_root,
                expected_name=name,
                expected_system_folder=db_root / "system",
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
            SYSTEM_FOLDER=str(db_root1 / "system"),
        ):
            from_env1 = Settings()  # Create settings object with envvars
            from_args = Settings(  # Create settings object with new values and check if envvars are updated
                DATABASE_NAME=name2,
                DATABASE_ROOT=db_root2,
                SYSTEM_FOLDER=db_root2 / "system",
            )

            from_env2 = Settings()  # Create settings object with updated envvars again

            # Assert
            self._assert_settings(
                from_args,
                mock_system(),
                expected_name=name2,
                expected_root=db_root2,
                expected_system_folder=db_root2 / "system",
            )

            assert from_env1 != from_args
            assert from_env1 != from_env2
            assert from_env2 == from_args
