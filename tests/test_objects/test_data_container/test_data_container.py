from pathlib import Path

import pytest

from flood_adapt.objects.data_container import (
    DataContainer,
)


class DummyContainer(DataContainer[str]):
    _extension: str = ".dummy"

    def _deserialize(self, path: Path, **kwargs) -> str:
        return path.read_text()

    def _serialize(self, path: Path, **kwargs) -> None:
        path.write_text(self._data or "")

    def _compare_data(self, data_a: str, data_b: str) -> bool:
        return data_a == data_b


def test_name_overwritten_from_path(tmp_path: Path):
    data_path = tmp_path / "my_data.dummy"
    data_path.touch()

    ref = DummyContainer(path=data_path)

    assert ref.name == "my_data"


def test_name_not_overwritten_if_explicit(tmp_path: Path):
    data_path = tmp_path / "my_data.dummy"
    data_path.touch()

    ref = DummyContainer(name="custom_name", path=data_path)

    assert ref.name == "custom_name"


def test_data_property_triggers_read(tmp_path: Path):
    data_path = tmp_path / "data_file.dummy"
    data_path.write_text("dummy-data")

    ref = DummyContainer(path=data_path)

    assert ref.has_data() is False

    data = ref.data

    assert data == "dummy-data"
    assert ref.has_data() is True


def test_has_data_flag(tmp_path: Path):
    data_path = tmp_path / "data_file.dummy"
    data_path.touch()

    ref = DummyContainer(path=data_path)

    assert ref.has_data() is False

    ref.read()

    assert ref.has_data() is True


def test_set_data_overwrites_internal_data():
    ref = DummyContainer(path="whatever.dummy")

    ref.set_data("manual-data")

    assert ref._data == "manual-data"
    assert ref.data == "manual-data"


def test_file_name_with_path(tmp_path: Path):
    data_path = tmp_path / "abc.dummy"
    data_path.touch()

    ref = DummyContainer(path=data_path)

    assert ref.file_name == "abc.dummy"


def test_file_name_without_path_uses_name_and_extension():
    ref = DummyContainer(name="test_name")

    assert ref.file_name == "test_name.dummy"


def test_equality_true_when_data_equal(tmp_path: Path):
    path1 = tmp_path / "a.dummy"
    path2 = tmp_path / "b.dummy"
    path1.touch()
    path2.touch()

    ref1 = DummyContainer(path=path1)
    ref2 = DummyContainer(path=path2)

    assert ref1 == ref2


def test_equality_false_for_different_types(tmp_path: Path):
    class OtherDummy(DummyContainer):
        pass

    path = tmp_path / "a.dummy"
    path.touch()

    ref1 = DummyContainer(path=path)
    ref2 = OtherDummy(path=path)

    assert ref1 != ref2


def test_serialize_path_uses_file_name(tmp_path: Path):
    data_path = tmp_path / "abc.dummy"
    data_path.touch()

    ref = DummyContainer(path=data_path)

    serialized = ref.model_dump()

    assert serialized["path"] == "abc.dummy"


def test_read_absolute_path_ignores_directory(tmp_path: Path):
    data_path = tmp_path / "data_file.dummy"
    data_path.write_text("dummy-data")

    ref = DummyContainer(path=data_path)

    # directory should be ignored
    ref.read(directory=tmp_path / "some_other_dir")

    assert ref._data == "dummy-data"


def test_datacontainer_missing_absolute_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        DummyContainer(path=tmp_path / "does_not_exist.dummy")


def test_read_relative_without_directory_raises():
    ref = DummyContainer(path="data_file.dummy")
    with pytest.raises(FileNotFoundError):
        ref.read()


def test_read_relative_with_directory(tmp_path: Path):
    data_path = tmp_path / "data_file.dummy"
    data_path.write_text("dummy-data")

    ref = DummyContainer(path=data_path.name)
    ref.read(directory=data_path.parent)

    assert ref._data == "dummy-data"


def test_write_to_original_path(tmp_path: Path):
    data_path = tmp_path / "out.dummy"
    data_path.write_text("dummy-data")

    ref = DummyContainer(path=data_path)
    ref.read()

    data_path.unlink()  # Remove file to test write
    ref.write()

    assert data_path.read_text() == "dummy-data"
