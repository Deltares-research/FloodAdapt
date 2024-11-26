import pytest
from object_model.hazard.event.forcing.forcing_factory import (
    FORCING_TYPES,
    ForcingFactory,
    ForcingSource,
    ForcingType,
)
from object_model.hazard.event.forcing.waterlevels import WaterlevelCSV


class TestForcingFactory:
    def test_get_forcing_class_valid(self):
        forcing_class = ForcingFactory.get_forcing_class(
            ForcingType.WATERLEVEL, ForcingSource.CSV
        )
        assert forcing_class == WaterlevelCSV

    def test_read_forcing(self, tmp_path):
        for expected_type, expected_sources in FORCING_TYPES.items():
            for expected_source, expected_class in expected_sources.items():
                if expected_class is None:
                    continue
                toml_file_path = (
                    tmp_path
                    / expected_type.value
                    / expected_source.value
                    / f"{expected_class.__class__.__name__}.toml"
                )
                if not toml_file_path.parent.exists():
                    toml_file_path.parent.mkdir(parents=True)
                with open(toml_file_path, "w") as f:
                    f.write(
                        f"_type = '{expected_type}'\n"
                        f"_source = '{expected_source}'\n",
                    )

                forcing_class, forcing_type, forcing_source = (
                    ForcingFactory.read_forcing(toml_file_path)
                )
                assert forcing_type == expected_type
                assert forcing_source == expected_source
                assert forcing_class == FORCING_TYPES[expected_type][expected_source]

    def test_get_forcing_class_invalid_type(self):
        with pytest.raises(ValueError):
            ForcingFactory().get_forcing_class("invalid_type", ForcingSource.CSV)

    def test_get_forcing_class_invalid_source(self):
        with pytest.raises(ValueError):
            ForcingFactory().get_forcing_class(ForcingType.WATERLEVEL, "invalid_source")

    def test_get_forcing_class_not_implemented(self):
        with pytest.raises(NotImplementedError):
            ForcingFactory().get_forcing_class(
                ForcingType.WATERLEVEL, ForcingSource.TRACK
            )
