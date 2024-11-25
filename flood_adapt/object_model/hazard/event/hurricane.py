import os
import shutil
from pathlib import Path
from typing import Any, ClassVar, List, Optional

import pyproj
from cht_cyclones.tropical_cyclone import TropicalCyclone
from pydantic import BaseModel
from shapely.affinity import translate

import flood_adapt.object_model.io.unitfulvalue as uv
from flood_adapt.object_model.hazard.event.forcing.forcing_factory import ForcingFactory
from flood_adapt.object_model.hazard.event.forcing.rainfall import RainfallTrack
from flood_adapt.object_model.hazard.event.forcing.wind import WindTrack
from flood_adapt.object_model.hazard.event.template_event import Event
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.hazard.interface.models import Mode, Template, TimeModel
from flood_adapt.object_model.interface.events import IEventModel
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.interface.site import Site
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: uv.UnitfulLength = uv.UnitfulLength(
        value=0.0, units=uv.UnitTypesLength.meters
    )
    northsouth_translation: uv.UnitfulLength = uv.UnitfulLength(
        value=0.0, units=uv.UnitTypesLength.meters
    )


class HurricaneEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [ForcingSource.TRACK],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.CSV],
    }

    hurricane_translation: TranslationModel
    track_name: str

    @classmethod
    def default(cls) -> "HurricaneEventModel":
        """Set default values for HurricaneEvent."""
        return HurricaneEventModel(
            name="DefaultHurricaneEvent",
            time=TimeModel(),
            template=Template.Hurricane,
            mode=Mode.single_event,
            hurricane_translation=TranslationModel(),
            track_name="",
            forcings={
                ForcingType.RAINFALL: ForcingFactory.get_default_forcing(
                    ForcingType.RAINFALL, ForcingSource.TRACK
                ),
                ForcingType.WIND: ForcingFactory.get_default_forcing(
                    ForcingType.WIND, ForcingSource.TRACK
                ),
                ForcingType.WATERLEVEL: ForcingFactory.get_default_forcing(
                    ForcingType.WATERLEVEL, ForcingSource.MODEL
                ),
                ForcingType.DISCHARGE: ForcingFactory.get_default_forcing(
                    ForcingType.DISCHARGE, ForcingSource.CONSTANT
                ),
            },
        )


class HurricaneEvent(Event):
    MODEL_TYPE = HurricaneEventModel

    attrs: HurricaneEventModel

    track_file: Path

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, HurricaneEventModel):
            self.attrs = data
        else:
            self.attrs = HurricaneEventModel.model_validate(data)

        self.site = Site.load_file(db_path(TopLevelDir.static) / "site" / "site.toml")
        self.track_file = (
            db_path(
                TopLevelDir.input, object_dir=self.dir_name, obj_name=self.attrs.name
            )
            / f"{self.attrs.track_name}.cyc"
        )

    def preprocess(self, output_dir: Path):
        spw_file = self.make_spw_file(output_dir=output_dir, recreate=True)
        for forcing in self.get_forcings():
            if isinstance(forcing, (RainfallTrack, WindTrack)):
                forcing.path = spw_file

    def make_spw_file(
        self,
        recreate: bool = False,
        output_dir: Optional[Path] = None,
    ) -> Path:
        """
        Create a spiderweb file from a given TropicalCyclone track and save it to the event's input directory.

        Providing the output_dir argument allows to save the spiderweb file in a different directory.

        Parameters
        ----------
        cyc_file : Path, optional
            Path to the cyc file, if None the .cyc file in the event's input directory is used
        recreate : bool, optional
            If True, the spiderweb file is recreated even if it already exists, by default False
        output_dir : Path, optional
            The directory where the spiderweb file is saved (or copied to if it already exists and recreate is False)
            By default it is saved in the same directory as the cyc file

        Returns
        -------
        Path
            the path to the created spiderweb file
        """
        spw_file = self.track_file.parent.joinpath(f"{self.attrs.track_name}.spw")

        output_dir = output_dir or self.track_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        if spw_file.exists() and not recreate:
            if spw_file != output_dir.joinpath(spw_file.name):
                shutil.copy2(spw_file, output_dir.joinpath(spw_file.name))
            return output_dir.joinpath(spw_file.name)
        elif spw_file.exists() and recreate:
            os.remove(spw_file)

        self.logger.info(
            f"Creating spiderweb file for hurricane event {self.attrs.name}..."
        )

        # Initialize the tropical cyclone
        tc = TropicalCyclone()
        tc.read_track(filename=self.track_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane_translation.northsouth_translation.value != 0
        ):
            tc = self.translate_tc_track(tc=tc)

        if self.attrs.forcings[ForcingType.RAINFALL] is not None:
            self.logger.info(
                f"Including rainfall in spiderweb file of hurricane {self.attrs.name}"
            )
            tc.include_rainfall = (
                self.attrs.forcings[ForcingType.RAINFALL]._source == ForcingSource.TRACK
            )

        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)
        if spw_file != output_dir.joinpath(spw_file.name):
            shutil.copy2(spw_file, output_dir.joinpath(spw_file.name))

        return output_dir.joinpath(spw_file.name)

    def translate_tc_track(self, tc: TropicalCyclone):
        self.logger.info("Translating the track of the tropical cyclone...")
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(self.site.attrs.sfincs.csname)
        tc.track = tc.track.to_crs(crs)

        # Translate the track in the local coordinate system
        tc.track["geometry"] = tc.track["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=self.attrs.hurricane_translation.eastwest_translation.convert(
                    "meters"
                ),
                yoff=self.attrs.hurricane_translation.northsouth_translation.convert(
                    "meters"
                ),
            )
        )

        # Convert the geodataframe to lat/lon
        tc.track = tc.track.to_crs(epsg=4326)

        return tc

    def save_additional(self, output_dir: Path | str | os.PathLike) -> None:
        default = (
            db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
            / f"{self.attrs.track_name}.cyc"
        )
        if self.track_file != default:
            src_path = resolve_filepath(
                self.dir_name,
                self.attrs.name,
                self.track_file,
            )
            path = save_file_to_database(src_path, Path(output_dir))
            self.track_file = path

        return super().save_additional(output_dir)
