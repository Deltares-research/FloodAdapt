import os
from pathlib import Path

import tomli
import tomli_w
from pydantic import BaseModel, Field


class Object(BaseModel):
    """Base class for FloodAdapt objects.

    Attributes
    ----------
    name : str
        Name of the object.
    description : str
        Description of the object. defaults to "".
    """

    name: str = Field(
        ...,
        description="Name of the object.",
        min_length=1,
        pattern='^[^<>:"/\\\\|?* ]*$',
    )
    description: str = Field(default="", description="Description of the object.")

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

    def __eq__(self, value):
        if not isinstance(value, self.__class__):
            # don't attempt to compare against unrelated types
            return False
        _self = self.model_dump(exclude={"name", "description"}, exclude_none=True)
        _other = value.model_dump(exclude={"name", "description"}, exclude_none=True)
        return _self == _other
