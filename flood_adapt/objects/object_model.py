import os
import re
from pathlib import Path

import tomli
import tomli_w
from pydantic import BaseModel, Field, field_validator


class Object(BaseModel):
    """Base class for FloodAdapt objects.

    Attributes
    ----------
    name : str
        Name of the object.
    description : str
        Description of the object. defaults to "".
    """

    name: str = Field(..., description="Name of the object.")
    description: str = Field(default="", description="Description of the object.")

    @field_validator("name")
    def validate_name(cls, value: str) -> str:
        if not len(value) > 0:
            raise ValueError("Name must be at least one character long.")
        if not re.match(r"^[A-Za-z0-9_-]+$", value):
            raise ValueError(
                "Name can only contain letters, numbers, underscores (_), and hyphens (-)."
            )
        return value

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike) -> "Object":
        """Load object from file.

        Parameters
        ----------
        file_path : Path | str | os.PathLike
            Path to the file to load.

        """
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        return cls.model_validate(toml)

    def save(self, toml_path: Path | str | os.PathLike) -> None:
        """Save object to disk.

        Parameters
        ----------
        toml_path : Path | str | os.PathLike
            Path to the file to save.

        """
        self.save_additional(output_dir=Path(toml_path).parent)
        with open(toml_path, "wb") as f:
            tomli_w.dump(self.model_dump(exclude_none=True), f)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save additional files to database if the object has any and update attrs to reflect the change in file location.

        This method should be overridden if the object has additional files.
        """
        pass

    def __eq__(self, other: "Object") -> bool:
        if not isinstance(other, self.__class__):
            return False
        # No need to check attributes here, ``name`` and ``description`` dont count toward equality
        # Subclasses should implement their own equality checks
        return True
