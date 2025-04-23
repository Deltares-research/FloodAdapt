from pathlib import Path
from typing import Type

import pytest

from flood_adapt.objects.forcing.forcing import IForcing
from flood_adapt.objects.forcing.forcing_factory import (
    ForcingFactory,
    ForcingSource,
    ForcingType,
)
from flood_adapt.objects.forcing.waterlevels import WaterlevelCSV


class TestForcingFactory:
    TYPE_SOURCE_CLASSES: set[tuple[ForcingType, ForcingSource, Type[IForcing]]] = {
        (
            forcing_type,
            forcing_source,
            ForcingFactory.FORCINGTYPES[forcing_type][forcing_source],
        )
        for forcing_type in ForcingFactory.FORCINGTYPES
        for forcing_source in ForcingFactory.FORCINGTYPES[forcing_type]
    }

    def test_get_forcing_class_valid(self):
        forcing_class = ForcingFactory.get_forcing_class(
            ForcingType.WATERLEVEL, ForcingSource.CSV
        )
        assert forcing_class == WaterlevelCSV

    @pytest.mark.parametrize(
        "expected_type, expected_source, expected_class",
        TYPE_SOURCE_CLASSES,
    )
    def test_read_forcing(
        self, tmp_path, expected_type, expected_source, expected_class
    ):
        toml_file_path: Path = (
            tmp_path
            / expected_type.value
            / expected_source.value
            / f"{expected_class.__class__.__name__}.toml"
        )
        if not toml_file_path.parent.exists():
            toml_file_path.parent.mkdir(parents=True)
        with open(toml_file_path, "w") as f:
            f.write(
                f"type = '{expected_type.value}'\nsource = '{expected_source.value}'\n",
            )

        forcing_class, forcing_type, forcing_source = ForcingFactory.read_forcing(
            toml_file_path
        )
        assert forcing_type == expected_type
        assert forcing_source == expected_source
        assert forcing_class == expected_class

    def test_get_forcing_class_invalid_type(self):
        with pytest.raises(ValueError):
            ForcingFactory().get_forcing_class("invalid_type", ForcingSource.CSV)

    def test_get_forcing_class_invalid_source(self):
        with pytest.raises(ValueError):
            ForcingFactory().get_forcing_class(ForcingType.WATERLEVEL, "invalid_source")

    def test_get_forcing_class_not_implemented(self):
        with pytest.raises(ValueError):
            ForcingFactory().get_forcing_class(
                ForcingType.WATERLEVEL, ForcingSource.TRACK
            )
