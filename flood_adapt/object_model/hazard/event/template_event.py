import os
from pathlib import Path
from typing import Any, List, Optional

import tomli
from pydantic import field_serializer, field_validator, model_validator

from flood_adapt.misc.config import Settings
from flood_adapt.object_model.hazard.forcing.discharge import DischargeCSV
from flood_adapt.object_model.hazard.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.forcing.rainfall import (
    RainfallCSV,
    RainfallNetCDF,
    RainfallTrack,
)
from flood_adapt.object_model.hazard.forcing.waterlevels import WaterlevelCSV
from flood_adapt.object_model.hazard.forcing.wind import WindCSV, WindNetCDF, WindTrack
from flood_adapt.object_model.hazard.interface.events import (
    ForcingSource,
    ForcingType,
    IEvent,
    IForcing,
)


class Event(IEvent):
    """The accepted input for an event in FloodAdapt.

    Attributes
    ----------
    name : str
        The name of the event.
    description : str, default=""
        The description of the event.
    time : TimeModel
        The time frame of the event.
    template : Template
        The template of the event.
    mode : Mode
        The mode of the event.
    rainfall_multiplier : float
        The rainfall multiplier of the event.
    forcings : dict[ForcingType, list[IForcing]]
        The forcings of the event.
    """

    @staticmethod
    def _parse_forcing_from_dict(
        forcing_attrs: dict[str, Any] | IForcing,
        ftype: Optional[ForcingType] = None,
        fsource: Optional[ForcingSource] = None,
    ) -> IForcing:
        if isinstance(forcing_attrs, IForcing):
            # forcing_attrs is already a forcing object
            return forcing_attrs
        elif isinstance(forcing_attrs, dict):
            # forcing_attrs is a dict with valid forcing attributes
            if "type" not in forcing_attrs and ftype:
                forcing_attrs["type"] = ftype
            if "source" not in forcing_attrs and fsource:
                forcing_attrs["source"] = fsource

            return ForcingFactory.load_dict(forcing_attrs)
        else:
            raise ValueError(
                f"Invalid forcing attributes: {forcing_attrs}. "
                "Forcings must be one of:\n"
                "1. Instance of IForcing\n"
                "2. dict with the keys `type` (ForcingType), `source` (ForcingSource) specifying the class, and with valid forcing attributes for that class."
            )

    @field_validator("forcings", mode="before")
    @classmethod
    def create_forcings(
        cls, value: dict[str, list[dict[str, Any]]]
    ) -> dict[ForcingType, list[IForcing]]:
        forcings = {}
        for ftype, forcing_list in value.items():
            ftype = ForcingType(ftype)
            forcings[ftype] = [
                Event._parse_forcing_from_dict(forcing, ftype)
                for forcing in forcing_list
            ]
        return forcings

    @model_validator(mode="after")
    def validate_forcings(self):
        def validate_concrete_forcing(concrete_forcing):
            type = concrete_forcing.type
            source = concrete_forcing.source

            # Check type
            if type not in self.__class__.ALLOWED_FORCINGS:
                allowed_types = ", ".join(
                    t.value for t in self.__class__.ALLOWED_FORCINGS.keys()
                )
                raise ValueError(
                    f"Forcing type {type.value} is not allowed. Allowed types are: {allowed_types}"
                )

            # Check source
            if source not in self.__class__.ALLOWED_FORCINGS[type]:
                allowed_sources = ", ".join(
                    s.value for s in self.__class__.ALLOWED_FORCINGS[type]
                )
                raise ValueError(
                    f"Forcing source {source.value} is not allowed for forcing type {type.value}. "
                    f"Allowed sources are: {allowed_sources}"
                )

        if Settings().validate_allowed_forcings:
            # Validate forcings
            for _, concrete_forcings in self.forcings.items():
                for concrete_forcing in concrete_forcings:
                    validate_concrete_forcing(concrete_forcing)

        return self

    @field_serializer("forcings")
    @classmethod
    def serialize_forcings(
        cls, value: dict[ForcingType, List[IForcing]]
    ) -> dict[str, List[dict[str, Any]]]:
        dct = {}
        for ftype, forcing_list in value.items():
            dct[ftype.value] = [
                forcing.model_dump(exclude_none=True) for forcing in forcing_list
            ]
        return dct

    @classmethod
    def get_allowed_forcings(cls) -> dict[str, List[str]]:
        return {k.value: [s.value for s in v] for k, v in cls.ALLOWED_FORCINGS.items()}

    def get_forcings(self) -> list[IForcing]:
        """Return a list of all forcings in the event."""
        return [forcing for forcings in self.forcings.values() for forcing in forcings]

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        """Save any additional files associated with the event."""
        for forcing in self.get_forcings():
            forcing.save_additional(output_dir)

    @classmethod
    def load_file(cls, file_path: Path | str | os.PathLike) -> "Event":
        """Load object from file.

        Parameters
        ----------
        file_path : Path | str | os.PathLike
            Path to the file to load.

        """
        with open(file_path, mode="rb") as fp:
            toml = tomli.load(fp)

        event = cls.model_validate(toml)

        # Update all forcings with paths to absolute paths
        for forcing in event.get_forcings():
            if isinstance(
                forcing,
                (
                    WaterlevelCSV,
                    RainfallTrack,
                    RainfallCSV,
                    RainfallNetCDF,
                    DischargeCSV,
                    WindTrack,
                    WindCSV,
                    WindNetCDF,
                ),
            ):
                if forcing.path.exists():
                    continue
                elif forcing.path == Path(forcing.path.name):
                    # convert relative path to absolute path
                    in_dir = Path(file_path).parent / forcing.path.name
                    if not in_dir.exists():
                        raise FileNotFoundError(
                            f"Failed to load Event. File {forcing.path} does not exist in {in_dir.parent}."
                        )
                    forcing.path = in_dir
                else:
                    raise FileNotFoundError(
                        f"Failed to load Event. File {forcing.path} does not exist."
                    )

        return event
