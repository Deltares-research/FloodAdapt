from pathlib import Path
from typing import TypeVar

from flood_adapt.objects.object_model import Object

T = TypeVar("T", bound=Object)


def assert_object_save_load_eq(
    write_path: Path, obj: T, cls: type[T], load_kwargs: dict | None = None
):
    test_path = write_path / "to_load.toml"
    test_path.parent.mkdir(exist_ok=True)

    obj.save(test_path)
    loaded = cls.load_file(test_path, **(load_kwargs or {}))

    assert loaded == obj
    return loaded
