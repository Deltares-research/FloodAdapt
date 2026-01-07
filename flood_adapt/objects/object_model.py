import os
import re
from pathlib import Path
from typing import TypeVar

import tomli
import tomli_w
from pydantic import BaseModel, Field, field_validator

T = TypeVar("T", bound="Object")


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
    def load_file(
        cls: type[T],
        file_path: Path | str | os.PathLike,
        load_all: bool = False,
        **kwargs,
    ) -> T:
        """Load object from file.

        Parameters
        ----------
        file_path : Path | str | os.PathLike
            Path to the file to load.

        """
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)
        obj = cls.model_validate(toml)
        if load_all:
            obj.read(directory=Path(file_path).parent, **kwargs)
        return obj

    def read(self, directory: Path | None = None, **kwargs) -> None:
        """Read additional files from disk.

        If any attributes reference external files, read them from disk and update the attributes accordingly.

        Parameters
        ----------
        **kwargs : dict
            Additional keyword arguments to pass to the read methods of any attributes that need to read from disk.

        This method should be overridden if the object has additional files.
        """
        pass

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

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            # don't attempt to compare against unrelated types
            return False
        _self = self.model_dump(exclude={"name", "description"}, exclude_none=True)
        _other = value.model_dump(exclude={"name", "description"}, exclude_none=True)
        return _self == _other
