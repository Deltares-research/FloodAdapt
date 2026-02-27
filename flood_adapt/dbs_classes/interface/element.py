from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Generic, Iterator, TypeVar

from flood_adapt.objects.object_model import Object

T_OBJECT_MODEL = TypeVar("T_OBJECT_MODEL", bound=Object)


class AbstractDatabaseElement(ABC, Generic[T_OBJECT_MODEL]):
    input_path: Path
    output_path: Path

    _objects: dict[str, T_OBJECT_MODEL]
    _mutated: set[str]
    _deleted: set[str]
    _last_modified: dict[str, datetime]

    @abstractmethod
    def __init__(self, database, standard_objects: list[str] | None = None) -> None: ...

    ## IO
    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...

    ## In memory mutations
    @abstractmethod
    def add(self, obj: T_OBJECT_MODEL, overwrite: bool = False) -> None: ...

    @abstractmethod
    def get(self, name: str) -> T_OBJECT_MODEL: ...

    @abstractmethod
    def copy(self, old_name: str, new_name: str, new_description: str) -> None: ...

    @abstractmethod
    def delete(self, name: str) -> None: ...

    @abstractmethod
    def clear(self) -> None: ...

    # Query
    @abstractmethod
    def summarize_objects(self) -> dict[str, list[Any]]: ...

    # Helpers
    @abstractmethod
    def used_by_higher_level(self, name: str) -> list[str]: ...

    @abstractmethod
    def list_all(self) -> list[T_OBJECT_MODEL]: ...

    # Special Python methods
    @abstractmethod
    def __del__(self) -> None: ...

    @abstractmethod
    def __len__(self) -> int: ...

    @abstractmethod
    def __contains__(self, name: str) -> bool: ...

    @abstractmethod
    def __iter__(self) -> Iterator[T_OBJECT_MODEL]: ...

    @abstractmethod
    def items(self) -> Iterator[tuple[str, T_OBJECT_MODEL]]: ...
