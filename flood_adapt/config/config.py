import re
import subprocess
from os import environ, listdir
from pathlib import Path
from tempfile import gettempdir
from typing import ClassVar, NoReturn, Optional

from pydantic import (
    Field,
    computed_field,
    field_serializer,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from flood_adapt.misc.io import read_toml, write_toml


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
    use_binaries : bool
        Whether to validate the existence of the paths to the SFINCS and FIAT binaries. Alias: `USE_BINARIES` (environment variable).
    sfincs_bin_path : Path
        The path to the SFINCS binary. Alias: `SFINCS_BIN_PATH` (environment variable).
    sfincs_version : str
        The expected version of the SFINCS binary. Alias: `SFINCS_VERSION` (environment variable).
    fiat_bin_path : Path
        The path to the FIAT binary. Alias: `FIAT_BIN_PATH` (environment variable).
    fiat_version : str
        The expected version of the FIAT binary. Alias: `FIAT_VERSION` (environment variable).

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
    use_binaries: bool = Field(
        alias="USE_BINARIES",  # environment variable: USE_BINARIES
        default=False,
        description="Whether to use the SFINCS and FIAT binaries. If True, the existence of the paths to the binaries will be validated. "
        "Their versions can be checked against the expected versions by manually calling `check_binary_versions`.",
        exclude=True,
    )

    sfincs_bin_path: Optional[Path] = Field(
        default=None,
        alias="SFINCS_BIN_PATH",  # environment variable: SFINCS_BIN_PATH
        description="The path of the sfincs binary.",
        exclude=True,
    )
    sfincs_version: str = Field(
        default="v2.2.1-alpha col d'Eze",
        alias="SFINCS_VERSION",  # environment variable: SFINCS_VERSION
        description="The expected version of the sfincs binary. If the version of the binary does not match this version, an error is raised.",
        exclude=True,
    )

    fiat_bin_path: Optional[Path] = Field(
        default=None,
        alias="FIAT_BIN_PATH",  # environment variable: FIAT_BIN_PATH
        description="The path of the fiat binary.",
        exclude=True,
    )
    fiat_version: str = Field(
        default="0.2.1",
        alias="FIAT_VERSION",  # environment variable: FIAT_VERSION
        description="The expected version of the fiat binary. If the version of the binary does not match this version, an error is raised.",
        exclude=True,
    )

    _binaries_validated: ClassVar[bool] = False

    @computed_field
    @property
    def database_path(self) -> Path:
        return self.database_root / self.database_name

    # Validators
    @model_validator(mode="after")
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

    @model_validator(mode="after")
    def _validate_sfincs_path(self):
        if self.use_binaries:
            if self.sfincs_bin_path is None:
                self._raise_exe_not_provided("sfincs")
            elif not self.sfincs_bin_path.exists():
                self._raise_exe_not_exists("sfincs", self.sfincs_bin_path)
        return self

    @model_validator(mode="after")
    def _validate_fiat_path(self):
        if self.use_binaries:
            if self.fiat_bin_path is None:
                self._raise_exe_not_provided("fiat")
            elif not self.fiat_bin_path.exists():
                self._raise_exe_not_exists("fiat", self.fiat_bin_path)
        return self

    @field_serializer("database_root", "database_path")
    def serialize_path(self, path: Path) -> str:
        return path.as_posix()

    @model_validator(mode="after")
    def _export_to_env(self):
        for k, v in Settings.model_fields.items():
            if v.alias is not None:
                env_key = v.alias
                value = getattr(self, k)
                self._export_env_var(env_key, value)
        return self

    # Public methods
    def export_to_env(self):
        """Manually export settings to environment variables. This is now called automatically during initialization."""
        self._export_to_env()

    def get_sfincs_version(self) -> str:
        """
        Get the version of the SFINCS binary.

        Returns
        -------
        str
            The version of the SFINCS binary

        Expected SFINCS output
        ----------------------

        ------------ Welcome to SFINCS ------------

        LOGO

        ------------------------------------------

        Build-Revision: $Rev: v2.2.1-alpha col d'Eze
        Build-Date: $Date: 2025-06-02

        ------ Preparing model simulation --------
        ...

        """
        if self.sfincs_bin_path is None:
            self._raise_exe_not_provided("sfincs")
        else:
            result = subprocess.run(
                [self.sfincs_bin_path.as_posix()],
                capture_output=True,
                text=True,
                cwd=gettempdir(),
            )

        # Capture everything after `$Rev:` until end of line
        match = re.search(r"Build-Revision:\s*\$Rev:\s*(.+)", result.stdout)
        if not match:
            self._raise_version_mismatch("sfincs", self.sfincs_version, "unknown")

        return match.group(1).strip()

    def get_fiat_version(self) -> str:
        """
        Get the version of the FIAT binary.

        Returns
        -------
        str
            The version of the FIAT binary

        Expected FIAT output
        --------------------

        FIAT 0.2.1, build 2025-02-24T16:19:19 UTC+0100
        ...

        """
        if self.fiat_bin_path is None:
            self._raise_exe_not_provided("fiat")

        result = subprocess.run(
            [self.fiat_bin_path.as_posix(), "--version"],
            capture_output=True,
            text=True,
            cwd=gettempdir(),
        )
        # Capture version number after 'FIAT' until the next whitespace
        fiat_match = re.search(r"FIAT\s+([0-9]+\.[0-9]+\.[0-9]+)", result.stdout)
        if not fiat_match:
            self._raise_version_mismatch("fiat", self.fiat_version, "unknown")
        return fiat_match.group(1).strip()

    def check_binary_versions(self) -> None:
        """Check that the versions of the binaries in the config match those expected."""
        if Settings._binaries_validated:
            return  # already validated

        if self.sfincs_bin_path is not None:
            if not self.sfincs_bin_path.exists():
                self._raise_exe_not_exists("sfincs", self.sfincs_bin_path)
            actual_sfincs_version = self.get_sfincs_version()
            if self.sfincs_version != actual_sfincs_version:
                self._raise_version_mismatch(
                    "sfincs", self.sfincs_version, actual_sfincs_version
                )

        if self.fiat_bin_path is not None:
            if not self.fiat_bin_path.exists():
                self._raise_exe_not_exists("fiat", self.fiat_bin_path)
            actual_fiat_version = self.get_fiat_version()
            if self.fiat_version != actual_fiat_version:
                self._raise_version_mismatch(
                    "fiat", self.fiat_version, actual_fiat_version
                )

        Settings._binaries_validated = True

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
        data = read_toml(toml_path)
        return Settings(**data)

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
        data = self.model_dump(
            by_alias=True,
            exclude={"sfincs_bin_path", "fiat_bin_path", "database_path"},
        )
        write_toml(data, toml_path)

    def _export_env_var(self, key: str, value: str | Path | bool | None) -> None:
        if isinstance(value, Path):
            environ[key] = value.as_posix()
        elif isinstance(value, (str, bool)):
            environ[key] = str(value)
        elif value is None:
            environ.pop(key, None)
        else:
            raise ValueError(
                f"Unsupported type for environment variable {key}: {type(value)}"
            )

    # Error helpers
    @staticmethod
    def _raise_exe_not_provided(model: str) -> NoReturn:
        raise ValueError(f"{model.upper()} binary path is not set.")

    @staticmethod
    def _raise_exe_not_exists(model: str, path: Path) -> NoReturn:
        raise ValueError(f"{model.upper()} binary does not exist: {path}.")

    @staticmethod
    def _raise_version_mismatch(model: str, expected: str, actual: str) -> NoReturn:
        raise ValueError(
            f"{model.upper()} version mismatch: expected {expected}, got {actual}."
        )
