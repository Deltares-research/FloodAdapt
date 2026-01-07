from pathlib import Path

import pytest
from cht_cyclones.tropical_cyclone import TropicalCyclone

from flood_adapt.objects import unit_system as us
from flood_adapt.objects.data_container import (
    CycloneTrackContainer,
    TranslationModel,
)


@pytest.fixture
def sample_cyclone_track(test_data_dir: Path) -> Path:
    return test_data_dir / "IAN.cyc"


def test_cyclone_track_read_write(tmp_path: Path, sample_cyclone_track: Path):
    ref1 = CycloneTrackContainer(path=sample_cyclone_track)
    ref1.read()

    assert isinstance(ref1._data, TropicalCyclone)
    out_path = tmp_path / "IAN_copy.ddb_cyc"
    ref1.path = out_path
    ref1.write()
    assert out_path.exists()

    ref2 = CycloneTrackContainer(path=out_path)
    ref2.read()

    assert ref1 == ref2


def test_cyclone_to_spw_creates_file(tmp_path, sample_cyclone_track):
    ref = CycloneTrackContainer(path=sample_cyclone_track)
    ref.read()

    out = ref.to_spw(directory=tmp_path)

    assert out.exists()
    assert out.suffix == ".spw"


def test_cyclone_to_spw_recreate(tmp_path, sample_cyclone_track):
    ref = CycloneTrackContainer(path=sample_cyclone_track)
    ref.read()

    out = ref.to_spw(directory=tmp_path)
    out.write_text("corrupted")

    out2 = ref.to_spw(directory=tmp_path, recreate=True)

    assert out2.exists()
    assert out2.read_text() != "corrupted"


def test_translate_track_zero_translation_noop(sample_cyclone_track):
    ref = CycloneTrackContainer(path=sample_cyclone_track)
    ref.read()

    original = ref.data.track.copy()

    translation = TranslationModel()
    ref.translate_track(translation)

    assert ref.data.track.equals(original)


def test_translate_track_moves_geometry(sample_cyclone_track):
    ref = CycloneTrackContainer(path=sample_cyclone_track)
    ref.read()

    original = ref.data.track.copy()

    translation = TranslationModel(
        eastwest_translation=us.UnitfulLength(
            value=1000, units=us.UnitTypesLength.meters
        ),
        northsouth_translation=us.UnitfulLength(
            value=1000, units=us.UnitTypesLength.meters
        ),
    )

    ref.translate_track(translation)

    assert not ref.data.track.equals(original)
