from os import environ, listdir
from pathlib import Path
from platform import system
from typing import ClassVar

import tomli
from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    The configuration settings for the FloodAdapt database and integrator.

    Precedence is as follows: user arguments > environment variables > defaults in this class.
    When loading is done, the settings are validated and the environment variables are updated with the loaded values.

    If any required settings are missing or invalid, a ValidationError is raised.

    Usage
    -----
    from flood_adapt.config import Settings

    # One of the following:
        # 1) Load settings from environment variables, if no environment variables are set, use defaults defined in the class:
        settings = Settings()

        # 2) Load settings from a .toml file, overwriting any environment variables set:
        settings = Settings.read(toml_path: Path)

        # 3) Load settings from keyword arguments, overwriting any environment variables:
        settings = Settings(database_root="path/to/database", database_name="database_name", system_folder="path/to/system_folder")

    Attributes
    ----------
    database_name : str
        The name of the database.
    database_root : Path
        The root directory of the database.
    system_folder : Path
        The root directory of the system folder.

    Properties
    ----------
    database_path : Path
        The full path to the database.
    sfincs_path : Path
        The path to the SFINCS binary.
    fiat_path : Path
        The path to the FIAT binary.

    Raises
    ------
    ValidationError
        If required settings are missing or invalid.
    """

    SYSTEM_SUFFIXES: ClassVar[dict[str, str]] = {
        "Windows": ".exe",
        "Linux": "",
        "Darwin": "",
    }

    model_config = SettingsConfigDict(
        env_ignore_empty=True, validate_default=True
    )  # empty env uses default

    database_root: Path = Field(
        default=Path(__file__).parents[2] / "Database", env="DATABASE_ROOT"
    )
    database_name: str = Field(default=None, min_length=1, env="DATABASE_NAME")
    system_folder: Path = Field(default=None, env="SYSTEM_FOLDER")

    @computed_field
    @property
    def sfincs_path(self) -> Path:
        return self.system_folder / "sfincs" / f"sfincs{Settings._system_extension()}"

    @computed_field
    @property
    def fiat_path(self) -> Path:
        return self.system_folder / "fiat" / f"fiat{Settings._system_extension()}"

    @computed_field
    @property
    def database_path(self) -> Path:
        return self.database_root / self.database_name

    @field_validator("database_root", mode="before")
    def set_database_root(cls, v, values):
        if not Path(v).is_dir():
            raise ValueError(f"Database root {v} does not exist.")
        return Path(v)

    @field_validator("database_name", mode="before")
    def set_database_name(cls, v, values):
        db_root = values.data.get(
            "database_root", Settings.model_fields["database_root"].default
        )
        if v is None:
            # If database_name is not given as arg or set in env, compute default as the first dir in database_root excluding 'system' (database_root set from env or default)
            sites = [
                d for d in listdir(db_root) if d != "system" and not d.startswith(".")
            ]
            if not sites:
                raise ValueError(f"No databases found in {db_root}.")
            return sites[0]

        if not (db_root / v).is_dir():
            raise ValueError(f"Database name {v} does not exist.")
        return v

    @field_validator("system_folder", mode="before")
    def set_system_folder(cls, v, values):
        if v is None:
            # If system_folder is not given as arg or set in env, compute default to database_root/system (database_root set from env or default)
            return (
                values.data.get("database_root", Path(__file__).parents[2] / "Database")
                / "system"
            )
        return v

    @model_validator(mode="after")
    def validate_paths(self):
        self._validate_database_path()
        self._validate_system_folder()
        self._validate_fiat_path()
        self._validate_sfincs_path()

        environ["DATABASE_ROOT"] = str(self.database_root)
        environ["DATABASE_NAME"] = self.database_name
        environ["SYSTEM_FOLDER"] = str(self.system_folder)

        return self

    def _validate_database_path(self):
        if not self.database_path.is_dir():
            raise ValueError(
                f"Database {self.database_name} at {self.database_root} does not exist. Full path: {self.database_path}"
            )

        if not (self.database_path / "input").is_dir():
            raise ValueError(
                f"Database {self.database_name} at {self.database_path} does not contain an input folder."
            )

        if not (self.database_path / "static").is_dir():
            raise ValueError(
                f"Database {self.database_name} at {self.database_path} does not contain a static folder."
            )

        return self

    def _validate_system_folder(self):
        if not self.system_folder.is_dir():
            raise ValueError(f"System folder {self.system_folder} does not exist.")
        return self

    def _validate_sfincs_path(self):
        if not self.sfincs_path.exists():
            raise ValueError(f"SFINCS binary {self.sfincs_path} does not exist.")
        return self

    def _validate_fiat_path(self):
        """Set FIAT path if not set, then validate it exists."""
        if not self.fiat_path.exists():
            raise ValueError(f"FIAT binary {self.fiat_path} does not exist.")
        return self

    @staticmethod
    def _system_extension() -> str:
        if system() not in Settings.SYSTEM_SUFFIXES:
            raise ValueError(f"Unsupported system {system()}")
        return Settings.SYSTEM_SUFFIXES[system()]

    @staticmethod
    def read(toml_path: Path) -> "Settings":
        """
        Parse the configuration file and return the parsed settings.

        Parameters
        ----------
        config_path : Path
            The path to the configuration file.

        Returns
        -------
        Settings
            The parsed configuration settings.

        Raises
        ------
        ValidationError
            If required configuration values are missing or if there is an error parsing the configuration file.
        """
        with open(toml_path, "rb") as f:
            settings = tomli.load(f)

        return Settings(**settings)
