from pathlib import Path
from unittest.mock import patch

from flood_adapt.config import Settings
from tests.utils import modified_environ


class TestSettingsModel:
    def test_init_no_env(self):
        with patch("flood_adapt.config.system") as mock_system:
            mock_system.return_value = "Windows"
            settings = Settings()
            assert settings.database_root == Path(__file__).parents[2] / "Database"
            assert settings.system_folder == settings.database_root / "system"
            assert settings.sfincs_path == settings.system_folder / "sfincs.exe"
            assert settings.fiat_path == settings.system_folder / "fiat" / "fiat.exe"

    def test_use_envvar_database_root(self, tmp_path: Path):
        with patch("flood_adapt.config.system") as mock_system:
            mock_system.return_value = "Darwin"
            with modified_environ(DATABASE_ROOT=str(tmp_path)):
                settings = Settings()
                assert settings.database_root == tmp_path
                assert settings.system_folder == settings.database_root / "system"
                assert settings.sfincs_path == settings.system_folder / "sfincs"
                assert settings.fiat_path == settings.system_folder / "fiat" / "fiat"
