from os import environ, listdir
from pathlib import Path
from typing import Optional

import tomli
import tomli_w
from pydantic import (
    Field,
    computed_field,
    field_serializer,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    The configuration settings for the FloodAdapt database and integrator.

    Precedence is as follows: user arguments > environment variables > defaults in this class.
    When loading is done, the settings are validated and the environment variables are updated with the loaded values.

    If any required settings are missing or invalid, a ValidationError is raised.

    Usage
    -----
    from flood_adapt import Settings

    One of the following:

    1) Load settings from environment variables, if no environment variables are set, use defaults defined in the class:
        `settings = Settings()`

    2) Load settings from a .toml file, overwriting any environment variables set:
        `settings = Settings.read(toml_path: Path)`

    3) Load settings from keyword arguments, overwriting any environment variables:
        `settings = Settings(DATABASE_ROOT="path/to/database", DATABASE_NAME="database_name")`

    Attributes
    ----------
    database_name : str
        The name of the database. Alias: `DATABASE_NAME` (environment variable).
    database_root : Path
        The root directory of the database. Alias: `DATABASE_ROOT` (environment variable).
    delete_crashed_runs : bool
        Whether to delete crashed/corrupted runs immediately after they are detected. Alias: `DELETE_CRASHED_RUNS` (environment variable).
    validate_allowed_forcings : bool
        Whether to validate the forcing types and sources against the allowed forcings in the event model. Alias: `VALIDATE_ALLOWED_FORCINGS` (environment variable).
    validate_binaries : bool
        Whether to validate the existence of the paths to the SFINCS and FIAT binaries. Alias: `VALIDATE_BINARIES` (environment variable).
    sfincs_bin_path : Path
        The path to the SFINCS binary. Alias: `SFINCS_BIN_PATH` (environment variable).
    fiat_bin_path : Path
        The path to the FIAT binary. Alias: `FIAT_BIN_PATH` (environment variable).

    Properties
    ----------
    database_path : Path
        The full path to the database.

    Raises
    ------
    ValidationError
        If required settings are missing or invalid.
    """

    model_config = SettingsConfigDict(env_ignore_empty=True, validate_default=True)

    database_root: Path = Field(
        alias="DATABASE_ROOT",  # environment variable DATABASE_ROOT
        default=Path(__file__).parents[3]
        / "Database",  # If you clone FloodAdapt, default is to look for the Database next to the FloodAdapt folder
        description="The root directory of the database that contains site(s). Usually the directory name is 'Database'. Default is to look for the Database in the same dir as the FloodAdapt cloned repo.",
    )
    database_name: str = Field(
        alias="DATABASE_NAME",  # environment variable DATABASE_NAME
        default="",
        description="The name of the database site, should be a folder inside the database root. The site must contain an 'input' and 'static' folder.",
    )

    delete_crashed_runs: bool = Field(
        alias="DELETE_CRASHED_RUNS",  # environment variable: DELETE_CRASHED_RUNS
        default=False,
        description="Whether to delete the output of crashed/corrupted runs. Be careful when setting this to False, as it may lead to a broken database that cannot be read in anymore.",
        exclude=True,
    )
    validate_allowed_forcings: bool = Field(
        alias="VALIDATE_ALLOWED_FORCINGS",  # environment variable: VALIDATE_ALLOWED_FORCINGS
        default=False,
        description="Whether to validate the forcing types and sources against the allowed forcings in the event model.",
        exclude=True,
    )
    validate_binaries: bool = Field(
        alias="VALIDATE_BINARIES",  # environment variable: VALIDATE_BINARIES
        default=False,
        description="Whether to validate the existence of the paths to the SFINCS and FIAT binaries.",
        exclude=True,
    )

    sfincs_bin_path: Optional[Path] = Field(
        default=None,
        alias="SFINCS_BIN_PATH",  # environment variable: SFINCS_BIN_PATH
        description="The path of the sfincs binary.",
        exclude=True,
    )

    fiat_bin_path: Optional[Path] = Field(
        default=None,
        alias="FIAT_BIN_PATH",  # environment variable: FIAT_BIN_PATH
        description="The path of the fiat binary.",
        exclude=True,
    )

    @computed_field
    @property
    def database_path(self) -> Path:
        return self.database_root / self.database_name

    @model_validator(mode="after")
    def validate_settings(self):
        self._validate_database_path()
        if self.validate_binaries:
            self._validate_fiat_path()
            self._validate_sfincs_path()
        self._update_environment_variables()
        return self

    def _update_environment_variables(self):
        environ["DATABASE_ROOT"] = str(self.database_root)
        environ["DATABASE_NAME"] = self.database_name

        if self.delete_crashed_runs:
            environ["DELETE_CRASHED_RUNS"] = str(self.delete_crashed_runs)
        else:
            environ.pop("DELETE_CRASHED_RUNS", None)

        if self.validate_allowed_forcings:
            environ["VALIDATE_ALLOWED_FORCINGS"] = str(self.validate_allowed_forcings)
        else:
            environ.pop("VALIDATE_ALLOWED_FORCINGS", None)

        if self.validate_binaries:
            environ["VALIDATE_BINARIES"] = str(self.validate_binaries)
            environ["SFINCS_BIN_PATH"] = str(self.sfincs_bin_path)
            environ["FIAT_BIN_PATH"] = str(self.fiat_bin_path)
        else:
            environ.pop("VALIDATE_BINARIES", None)

        return self

    def _validate_database_path(self):
        if not self.database_root.is_dir():
            raise ValueError(f"Database root {self.database_root} does not exist.")

        if self.database_name == "":
            # If database_name is not given as arg or set in env, compute default as the first dir in database_root excluding 'system'
            sites = [
                d
                for d in listdir(self.database_root)
                if d != "system" and not d.startswith(".")
            ]
            if not sites:
                raise ValueError(f"No databases found in {self.database_root}.")
            self.database_name = sites[0]

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

    def _validate_sfincs_path(self):
        if not self.sfincs_bin_path.exists():
            raise ValueError(f"SFINCS binary {self.sfincs_bin_path} does not exist.")
        return self

    def _validate_fiat_path(self):
        if not self.fiat_bin_path.exists():
            raise ValueError(f"FIAT binary {self.fiat_bin_path} does not exist.")
        return self

    @field_serializer("database_root", "database_path")
    def serialize_path(self, path: Path) -> str:
        return str(path)

    @staticmethod
    def read(toml_path: Path) -> "Settings":
        """
        Parse the configuration file and return the parsed settings.

        Parameters
        ----------
        toml_path : Path
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

    def write(self, toml_path: Path) -> None:
        """
        Write the configuration settings to a .toml file.

        Parameters
        ----------
        toml_path : Path
            The path to the configuration file.

        Returns
        -------
        None

        """
        toml_path = Path(toml_path).resolve()
        if not toml_path.parent.exists():
            toml_path.parent.mkdir(parents=True, exist_ok=True)

        with open(toml_path, "wb") as f:
            tomli_w.dump(
                self.model_dump(
                    by_alias=True,
                    exclude={"sfincs_bin_path", "fiat_bin_path", "database_path"},
                ),
                f,
            )
