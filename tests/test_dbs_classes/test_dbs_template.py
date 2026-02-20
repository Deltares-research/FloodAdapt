from pathlib import Path

import pytest
import tomli_w
import tomllib

from flood_adapt.dbs_classes import DbsTemplate
from flood_adapt.misc.exceptions import (
    AlreadyExistsError,
    DoesNotExistError,
    IsStandardObjectError,
)


class FakeObject:
    def __init__(self, name, description="desc"):
        self.name = name
        self.description = description

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            tomli_w.dump({"name": self.name, "description": self.description}, f)

    @classmethod
    def load_file(cls, path: Path):
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)

    def model_copy(self, deep=True):
        return FakeObject(self.name, self.description)

    def model_validate(self, _):
        pass


class FakeRepo(DbsTemplate[FakeObject]):
    dir_name = "objects"
    display_name = "Object"
    _object_class = FakeObject
    _higher_lvl_object = "Parent"


class FakeDB:
    def __init__(self, base):
        self.input_path = base / "input"
        self.output_path = base / "output"


def test_load(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    obj = FakeObject("a")
    obj.save(tmp_path / "input/objects/a/a.toml")

    repo.load()

    assert repo.get("a").name == "a"
    assert repo._mutated == set(), "loading must not stage mutations"


def test_add_and_flush(tmp_path: Path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)
    obj = FakeObject("b")
    expected_path = repo.input_path / obj.name / f"{obj.name}.toml"

    repo.add(obj)
    assert not expected_path.exists()
    assert obj.name in repo._mutated

    repo.flush()
    assert expected_path.exists()
    assert repo._mutated == set()


def test_delete_and_flush(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)
    obj = FakeObject("c")
    expected_path = repo.input_path / obj.name / f"{obj.name}.toml"

    repo.add(obj)
    repo.flush()
    assert expected_path.exists()

    repo.delete("c")
    assert expected_path.exists()
    assert obj.name in repo._deleted

    repo.flush()
    assert not expected_path.parent.exists()
    assert repo._mutated == set()


def test_copy_is_deep(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    repo.add(FakeObject("orig", "hello"))
    repo.copy("orig", "clone", "new")

    clone = repo.get("clone")
    clone.description = "changed"

    # original must remain untouched
    assert repo.get("orig").description == "hello"


def test_add_duplicate_without_overwrite_raises(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)
    obj = FakeObject("x")
    repo.add(obj)

    with pytest.raises(AlreadyExistsError):
        repo.add(obj, overwrite=False)


def test_add_duplicate_with_overwrite(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)
    obj = FakeObject("x")
    repo.add(obj)
    repo.add(obj, overwrite=True)
    assert obj.name in repo._mutated


def test_standard_object_protected(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db, standard_objects=["std"])

    repo._objects["std"] = FakeObject("std")

    with pytest.raises(IsStandardObjectError):
        repo.delete("std")


def test_get_returns_copy(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)
    obj = FakeObject("safe")

    repo.add(obj)

    copied = repo.get("safe")
    copied.description = "mutated"

    assert repo.get("safe").description == obj.description


def test_flush_is_idempotent(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    repo.add(FakeObject("a"))
    repo.flush()

    # second flush should do nothing, and not error
    repo.flush()

    assert repo._mutated == set()
    assert repo._deleted == set()


def test_add_then_delete_before_flush(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    repo.add(FakeObject("temp"))
    repo.delete("temp")

    repo.flush()

    assert not (repo.input_path / "temp").exists()


def test_overwrite_replaces_disk_content(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    repo.add(FakeObject("x", "old"))
    repo.flush()

    repo.add(FakeObject("x", "new"), overwrite=True)
    repo.flush()

    loaded = FakeObject.load_file(repo.input_path / "x/x.toml")

    assert loaded.description == "new"


def test_load_twice_is_safe(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    FakeObject("a").save(tmp_path / "input/objects/a/a.toml")

    repo.load()
    repo.load()

    assert len(repo.list_all()) == 1
    assert repo._mutated == set()


def test_get_missing_raises(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    with pytest.raises(DoesNotExistError):
        repo.get("not_exists")


def test_delete_missing_raises(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    with pytest.raises(DoesNotExistError):
        repo.delete("not_exists")


def test_mutating_returned_object_does_not_stage_mutation(tmp_path):
    db = FakeDB(tmp_path)
    repo = FakeRepo(db)

    repo.add(FakeObject("safe"))
    repo.flush()

    obj = repo.get("safe")
    obj.description = "changed"

    assert "safe" not in repo._mutated
