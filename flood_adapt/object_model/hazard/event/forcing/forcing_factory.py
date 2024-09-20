from pathlib import Path
from typing import Any, List

import tomli

from flood_adapt.object_model.hazard.event.forcing.discharge import (
    DischargeConstant,
    DischargeFromCSV,
    DischargeSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.rainfall import (
    RainfallConstant,
    RainfallFromMeteo,
    RainfallFromTrack,
    RainfallSynthetic,
)

# RainfallfromCSV,
from flood_adapt.object_model.hazard.event.forcing.waterlevels import (
    WaterlevelFromCSV,
    WaterlevelFromGauged,
    WaterlevelFromModel,
    WaterlevelSynthetic,
)
from flood_adapt.object_model.hazard.event.forcing.wind import (
    WindConstant,
    WindFromCSV,
    WindFromMeteo,
    WindFromTrack,
    WindSynthetic,
)
from flood_adapt.object_model.hazard.interface.forcing import (
    IForcing,
    IForcingFactory,
)
from flood_adapt.object_model.hazard.interface.models import (
    ForcingSource,
    ForcingType,
)

FORCING_TYPES: dict[ForcingType, dict[ForcingSource, IForcing]] = {
    ForcingType.WATERLEVEL: {
        ForcingSource.MODEL: WaterlevelFromModel,
        ForcingSource.TRACK: None,
        ForcingSource.CSV: WaterlevelFromCSV,
        ForcingSource.SYNTHETIC: WaterlevelSynthetic,
        ForcingSource.CONSTANT: None,
        ForcingSource.GAUGED: WaterlevelFromGauged,
    },
    ForcingType.RAINFALL: {
        ForcingSource.METEO: RainfallFromMeteo,
        ForcingSource.TRACK: RainfallFromTrack,
        ForcingSource.CSV: None,
        ForcingSource.SYNTHETIC: RainfallSynthetic,
        ForcingSource.CONSTANT: RainfallConstant,
    },
    ForcingType.WIND: {
        ForcingSource.METEO: WindFromMeteo,
        ForcingSource.TRACK: WindFromTrack,
        ForcingSource.CSV: WindFromCSV,
        ForcingSource.SYNTHETIC: WindSynthetic,
        ForcingSource.CONSTANT: WindConstant,
    },
    ForcingType.DISCHARGE: {
        ForcingSource.MODEL: None,
        ForcingSource.TRACK: None,
        ForcingSource.CSV: DischargeFromCSV,
        ForcingSource.SYNTHETIC: DischargeSynthetic,
        ForcingSource.CONSTANT: DischargeConstant,
    },
}


class ForcingFactory(IForcingFactory):
    """Factory class for creating forcing events based on a template."""

    @staticmethod
    def read_forcing(
        filepath: Path,
    ) -> tuple[IForcing, ForcingType, ForcingSource]:
        """Extract forcing type and source from a TOML file."""
        with open(filepath, mode="rb") as fp:
            toml_data = tomli.load(fp)
        _type = toml_data.get("_type")
        _source = toml_data.get("_source")

        if _type is None or _source is None:
            raise ValueError(
                f"Forcing type {_type} or source {_source} not found in {filepath}"
            )
        _cls = ForcingFactory.get_forcing_class(
            ForcingType(_type), ForcingSource(_source)
        )
        return _cls, ForcingType(_type), ForcingSource(_source)

    @staticmethod
    def get_forcing_class(_type: ForcingType, source: ForcingSource) -> IForcing:
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
    def load_file(toml_file: Path) -> IForcing:
        """Create a forcing object from a TOML file."""
        with open(toml_file, mode="rb") as fp:
            toml_data = tomli.load(fp)
        _ = ForcingFactory.read_forcing(toml_file)
        return ForcingFactory.load_dict(toml_data)

    @staticmethod
    def load_dict(attrs: dict[str, Any]) -> IForcing:
        """Create a forcing object from a dictionary of attributes."""
        _type = attrs.get("_type")
        _source = attrs.get("_source")
        if _type is None or _source is None:
            raise ValueError(
                f"Forcing type {_type} or source {_source} not found in attributes."
            )
        return ForcingFactory.get_forcing_class(
            ForcingType(_type), ForcingSource(_source)
        ).model_validate(attrs)

    @staticmethod
    def list_forcing_types() -> List[str]:
        """List all available forcing types."""
        return [ftype.value for ftype in FORCING_TYPES.keys()]

    @staticmethod
    def list_forcings(as_string: bool = True) -> List[str | IForcing]:
        """List all available forcing classes."""
        forcing_classes = set()
        for source_map in FORCING_TYPES.values():
            for forcing in source_map.values():
                if forcing is not None:
                    if as_string:
                        forcing = forcing.__name__
                    forcing_classes.add(forcing)
        return forcing_classes

    @staticmethod
    def get_default_forcing(_type: ForcingType, source: ForcingSource) -> IForcing:
        """Get the default forcing object for a given type and source."""
        forcing_class = FORCING_TYPES[_type][source]
        if forcing_class is None:
            raise NotImplementedError(
                f"Forcing class for {_type} and {source} is not implemented."
            )
        return forcing_class.default()
