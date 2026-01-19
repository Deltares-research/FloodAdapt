import os
import re
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from flood_adapt.misc.io import read_toml, write_toml


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
        toml = read_toml(file_path)
        return cls.model_validate(toml)

    def save(self, toml_path: Path | str | os.PathLike) -> None:
        """Save object to disk.

        Parameters
        ----------
        toml_path : Path | str | os.PathLike
            Path to the file to save.

        """
        self.save_additional(output_dir=Path(toml_path).parent)
        write_toml(self.model_dump(exclude_none=True), toml_path)

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save additional files to database if the object has any and update attrs to reflect the change in file location.

        This method should be overridden if the object has additional files.
        """
        pass

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            # don't attempt to compare against unrelated types
            return False
        _self = self.model_dump(exclude={"name", "description"}, exclude_none=True)
        _other = value.model_dump(exclude={"name", "description"}, exclude_none=True)
        return _self == _other
