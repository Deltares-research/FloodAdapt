from pathlib import Path
from typing import Any, List, Type

import tomli

from flood_adapt.objects.forcing.discharge import (
    DischargeConstant,
    DischargeCSV,
    DischargeSynthetic,
)
from flood_adapt.objects.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
    IForcingFactory,
)
from flood_adapt.objects.forcing.rainfall import (
    RainfallConstant,
    RainfallCSV,
    RainfallMeteo,
    RainfallNetCDF,
    RainfallSynthetic,
    RainfallTrack,
)
from flood_adapt.objects.forcing.waterlevels import (
    WaterlevelCSV,
    WaterlevelGauged,
    WaterlevelModel,
    WaterlevelSynthetic,
)
from flood_adapt.objects.forcing.wind import (
    WindConstant,
    WindCSV,
    WindMeteo,
    WindNetCDF,
    WindSynthetic,
    WindTrack,
)

__all__ = [
    "ForcingFactory",
    "ForcingSource",
    "ForcingType",
    "IForcing",
    "IForcingFactory",
    "WindConstant",
    "WindCSV",
    "WindMeteo",
    "WindSynthetic",
    "WindTrack",
    "WaterlevelCSV",
    "WaterlevelGauged",
    "WaterlevelModel",
    "WaterlevelSynthetic",
    "RainfallConstant",
    "RainfallCSV",
    "RainfallMeteo",
    "RainfallSynthetic",
    "RainfallTrack",
    "DischargeConstant",
    "DischargeCSV",
    "DischargeSynthetic",
]


class ForcingFactory(IForcingFactory):
    """Factory class for creating forcings."""

    WATERLEVELS: dict[ForcingSource, Type[IForcing]] = {
        ForcingSource.MODEL: WaterlevelModel,
        ForcingSource.CSV: WaterlevelCSV,
        ForcingSource.SYNTHETIC: WaterlevelSynthetic,
        ForcingSource.GAUGED: WaterlevelGauged,
    }

    WIND: dict[ForcingSource, Type[IForcing]] = {
        ForcingSource.METEO: WindMeteo,
        ForcingSource.TRACK: WindTrack,
        ForcingSource.CSV: WindCSV,
        ForcingSource.SYNTHETIC: WindSynthetic,
        ForcingSource.CONSTANT: WindConstant,
        ForcingSource.NETCDF: WindNetCDF,
    }

    RAINFALL: dict[ForcingSource, Type[IForcing]] = {
        ForcingSource.METEO: RainfallMeteo,
        ForcingSource.TRACK: RainfallTrack,
        ForcingSource.CSV: RainfallCSV,
        ForcingSource.SYNTHETIC: RainfallSynthetic,
        ForcingSource.CONSTANT: RainfallConstant,
        ForcingSource.NETCDF: RainfallNetCDF,
    }

    DISCHARGE: dict[ForcingSource, Type[IForcing]] = {
        ForcingSource.CSV: DischargeCSV,
        ForcingSource.SYNTHETIC: DischargeSynthetic,
        ForcingSource.CONSTANT: DischargeConstant,
    }

    FORCINGTYPES: dict[ForcingType, dict[ForcingSource, Type[IForcing]]] = {
        ForcingType.WATERLEVEL: WATERLEVELS,
        ForcingType.RAINFALL: RAINFALL,
        ForcingType.WIND: WIND,
        ForcingType.DISCHARGE: DISCHARGE,
    }

    @classmethod
    def read_forcing(
        cls,
        filepath: Path,
    ) -> tuple[Type[IForcing], ForcingType, ForcingSource]:
        """Extract forcing type and source from a TOML file."""
        with open(filepath, mode="rb") as fp:
            toml_data = tomli.load(fp)
        type = toml_data.get("type")
        source = toml_data.get("source")

        if type is None or source is None:
            raise ValueError(
                f"Forcing type {type} or source {source} not found in {filepath}"
            )
        forcing_cls = cls.get_forcing_class(ForcingType(type), ForcingSource(source))
        return forcing_cls, ForcingType(type), ForcingSource(source)

    @classmethod
    def get_forcing_class(
        cls, type: ForcingType, source: ForcingSource
    ) -> Type[IForcing]:
        """Get the forcing class corresponding to the type and source."""
        if (sources := cls.FORCINGTYPES.get(type)) is None:
            raise ValueError(f"Invalid forcing type: {type}")

        if (forcing_cls := sources.get(source)) is None:
            raise ValueError(
                f"Invalid forcing source: {source} for forcing type: {type}"
            )
        return forcing_cls

    @classmethod
    def load_file(cls, toml_file: Path) -> IForcing:
        """Create a forcing object from a TOML file."""
        with open(toml_file, mode="rb") as fp:
            toml_data = tomli.load(fp)
        return cls.load_dict(toml_data)

    @classmethod
    def load_dict(cls, attrs: dict[str, Any] | IForcing) -> IForcing:
        """Create a forcing object from a dictionary of attributes."""
        if isinstance(attrs, IForcing):
            return attrs
        type = attrs.get("type")
        source = attrs.get("source")
        if type is None or source is None:
            raise ValueError(
                f"Forcing type {type} or source {source} not found in attributes."
            )
        return cls.get_forcing_class(
            ForcingType(type), ForcingSource(source)
        ).model_validate(attrs)

    @classmethod
    def list_forcings(cls) -> List[Type[IForcing]]:
        """List all available forcing classes."""
        forcing_classes = set()
        for source_map in cls.FORCINGTYPES.values():
            for forcing in source_map.values():
                if forcing is not None:
                    forcing_classes.add(forcing)
        return list(forcing_classes)

    @classmethod
    def list_forcing_types_and_sources(cls) -> List[tuple[ForcingType, ForcingSource]]:
        """List all available forcing classes using a tuple of ForcingType and ForcingSource."""
        # TODO remove this when the backend supports all forcings
        ONLY_BACKEND_FORCINGS = {(ForcingType.WIND, ForcingSource.SYNTHETIC)}
        combinations = set()
        for type, source_map in cls.FORCINGTYPES.items():
            for source in source_map.keys():
                if (type, source) in ONLY_BACKEND_FORCINGS:
                    continue
                combinations.add((type, source))
        return list(combinations)
