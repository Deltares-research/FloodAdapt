from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from flood_adapt.objects.object_model import Object

T_OBJECT_MODEL = TypeVar("T_OBJECT_MODEL", bound=Object)


class AbstractDatabaseElement(ABC, Generic[T_OBJECT_MODEL]):
    input_path: Path
    output_path: Path
    _objects: dict[str, T_OBJECT_MODEL]

    @abstractmethod
    def __init__(self, database, standard_objects: list[str] | None = None): ...

    ## IO
    @abstractmethod
    def load(self): ...

    @abstractmethod
    def flush(self): ...

    ## In memory mutations
    @abstractmethod
    def add(self, obj: T_OBJECT_MODEL, overwrite: bool = False) -> None: ...

    @abstractmethod
    def get(self, name: str) -> T_OBJECT_MODEL: ...

    @abstractmethod
    def copy(self, old_name: str, new_name: str, new_description: str): ...

    @abstractmethod
    def delete(self, name: str, toml_only: bool = False): ...

    # Query
    @abstractmethod
    def summarize_objects(self) -> dict[str, list[Any]]: ...

    # Helpers
    @abstractmethod
    def used_by_higher_level(self, name: str) -> list[str]: ...

    @abstractmethod
    def list_all(self) -> list[T_OBJECT_MODEL]: ...
