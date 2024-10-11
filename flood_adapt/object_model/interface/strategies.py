import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class StrategyModel(BaseModel):
    name: str = Field(..., min_length=1, pattern='^[^<>:"/\\\\|?* ]*$')
    description: Optional[str] = ""
    measures: Optional[list[str]] = []


class IStrategy(ABC):
    attrs: StrategyModel
    database_input_path: Union[str, os.PathLike]

    @staticmethod
    @abstractmethod
    def load_file(filepath: Union[str, os.PathLike], validate: bool = False):
        """Get Strategy attributes from toml file."""
        ...

    @staticmethod
    @abstractmethod
    def load_dict(
        data: dict[str, Any],
        database_input_path: Union[str, os.PathLike],
        validate: bool = True,
    ):
        """Get Strategy attributes from an object, e.g. when initialized from GUI."""
        ...

    @abstractmethod
    def save(self, filepath: Union[str, os.PathLike]):
        """Save Strategy attributes to a toml file."""

    @abstractmethod
    def save_additional_files(self, input_dir: Path):
        """Save additional files to the objects input directory."""
        ...
