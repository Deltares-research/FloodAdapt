from pathlib import Path
from platform import system
from typing import Any, Dict, Union

import tomli
from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_ignore_empty=True, validate_default=True
    )  # empty env uses default

    database_root: Path = Field(default=Path(__file__).parents[2] / "Database")
    system_folder: Path
    database_name: str = Field(default="default")
    sfincs_path: Path
    fiat_path: Path

    @computed_field
    @property
    def database_path(self) -> Path:
        return self.database_root / self.database_name

    @model_validator(mode="before")
    def set_defaults_if_missing(cls, data: Any) -> "Settings":
        if isinstance(data, dict):
            cls._validate_system_folder(data)
            cls._validate_fiat_path(data)
            cls._validate_sfincs_path(data)
        return data

    @classmethod
    def _validate_system_folder(cls, data: Dict[str, Any]):
        """Set system_folder path if not set."""
        field_name: str = "system_folder"
        system_folder: Any = data.get(field_name)
        if system_folder is None:
            # base system folder on database root.
            database_root: Union[Path, str] = (
                data.get("database_root") or cls.model_fields["database_root"].default
            )
            database_root: Path = Path(database_root)
            data[field_name] = database_root / "system"

    @classmethod
    def _validate_sfincs_path(cls, data: Dict[str, Any]):
        """Set SFINCS path if not set."""
        field_name: str = "sfincs_path"
        sfincs_path: Any = data.get(field_name)
        if sfincs_path is None:
            system_folder: Path = data.get("system_folder")
            if system() == "Windows":
                data[field_name] = system_folder / "sfincs.exe"
            else:
                data[field_name] = system_folder / "sfincs"

    @classmethod
    def _validate_fiat_path(cls, data: Any) -> Path:
        """Set FIAT path if not set."""
        field_name: str = "fiat_path"
        fiat_path: Any = data.get(field_name)
        if fiat_path is None:
            system_folder: Path = data.get("system_folder")
            if system() == "Windows":
                data[field_name] = system_folder / "fiat" / "fiat.exe"
            else:
                data[field_name] = system_folder / "fiat" / "fiat"


settings = Settings()


def parse_config(config_path: Path) -> Settings:
    """
    Parse the configuration file and return the parsed settings.

    Parameters
    ----------
    config_path : Path
        The path to the configuration file.

    Returns
    -------
    dict
        The parsed configuration dictionary.

    Raises
    ------
    ValueError
        If required configuration values are missing or if there is an error parsing the configuration file.
    """
    with open(config_path, "rb") as f:
        config = tomli.load(f)

    return Settings(config)
