from pathlib import Path
from typing import Any

import tomli

from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
    IForcingFactory,
)

from .discharge import DischargeFromCSV, DischargeSynthetic
from .rainfall import (
    RainfallConstant,
    RainfallFromModel,
    RainfallFromSPWFile,
    RainfallFromTrack,
    RainfallSynthetic,
)
from .waterlevels import (
    WaterlevelFromCSV,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from .wind import WindConstant, WindFromModel, WindFromTrack, WindSynthetic

FORCING_TYPES: dict[ForcingType, dict[ForcingSource, IForcing]] = {
    ForcingType.WATERLEVEL: {
        ForcingSource.MODEL: WaterlevelFromModel,
        ForcingSource.TRACK: None,
        ForcingSource.CSV: WaterlevelFromCSV,
        ForcingSource.SYNTHETIC: WaterlevelSynthetic,
        ForcingSource.SPW_FILE: None,
        ForcingSource.CONSTANT: None,
    },
    ForcingType.RAINFALL: {
        ForcingSource.MODEL: RainfallFromModel,
        ForcingSource.TRACK: RainfallFromTrack,
        ForcingSource.CSV: None,
        ForcingSource.SYNTHETIC: RainfallSynthetic,
        ForcingSource.SPW_FILE: RainfallFromSPWFile,
        ForcingSource.CONSTANT: RainfallConstant,
        ForcingSource.METEO: None,
    },
    ForcingType.WIND: {
        ForcingSource.MODEL: WindFromModel,
        ForcingSource.TRACK: WindFromTrack,
        ForcingSource.CSV: None,
        ForcingSource.SYNTHETIC: WindSynthetic,
        ForcingSource.SPW_FILE: None,
        ForcingSource.CONSTANT: WindConstant,
        ForcingSource.METEO: None,
    },
    ForcingType.DISCHARGE: {
        ForcingSource.MODEL: None,
        ForcingSource.TRACK: None,
        ForcingSource.CSV: DischargeFromCSV,
        ForcingSource.SYNTHETIC: DischargeSynthetic,
        ForcingSource.SPW_FILE: None,
        ForcingSource.CONSTANT: None,
        ForcingSource.METEO: None,
    },
}


class ForcingFactory(IForcingFactory):
    """Factory class for creating forcing events based on a template."""

    @classmethod
    def get_forcing_class(cls, _type: ForcingType, source: ForcingSource) -> IForcing:
        """Get the forcing class corresponding to the type and source."""
        if _type not in FORCING_TYPES:
            raise ValueError(f"Invalid forcing type: {_type}")
        if source not in FORCING_TYPES[_type]:
            raise ValueError(
                f"Invalid forcing source: {source} for forcing type: {_type}"
            )

        forcing_class = FORCING_TYPES[_type][source]
        if forcing_class is None:
            raise NotImplementedError(
                f"Forcing class for {_type} and {source} is not implemented."
            )
        return forcing_class

    @staticmethod
    def read_forcing_type_and_source(
        filepath: Path,
    ) -> tuple[ForcingType, ForcingSource]:
        """Extract forcing type and source from a TOML file."""
        with open(filepath, mode="rb") as fp:
            toml_data = tomli.load(fp)
        _type = toml_data.get("_type")
        _source = toml_data.get("_source")
        if _type is None or _source is None:
            raise ValueError(
                f"Forcing type {_type} or source {_source} not found in {filepath}"
            )
        return ForcingType(_type), ForcingSource(_source)

    @classmethod
    def load_file(cls, toml_file: Path) -> IForcing:
        """Create a forcing object from a TOML file."""
        with open(toml_file, mode="rb") as fp:
            toml_data = tomli.load(fp)
        _type, _source = cls.read_forcing_type_and_source(toml_file)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs: dict[str, Any]) -> IForcing:
        """Create a forcing object from a dictionary of attributes."""
        _type = attrs.get("_type")
        _source = attrs.get("_source")
        if _type is None or _source is None:
            raise ValueError(
                f"Forcing type {_type} or source {_source} not found in attributes."
            )
        return cls.get_forcing_class(
            ForcingType(_type), ForcingSource(_source)
        ).model_validate(attrs)
