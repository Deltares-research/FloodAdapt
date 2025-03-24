import math
import os
from pathlib import Path
from typing import Any, ClassVar, List

import pyproj
from cht_cyclones.tropical_cyclone import TropicalCyclone
from pydantic import BaseModel
from shapely.affinity import translate

from flood_adapt.object_model.hazard.event.template_event import Event, EventModel
from flood_adapt.object_model.hazard.forcing.rainfall import RainfallTrack
from flood_adapt.object_model.hazard.forcing.wind import WindTrack
from flood_adapt.object_model.hazard.interface.events import Template
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.interface.config.site import Site
from flood_adapt.object_model.interface.path_builder import (
    TopLevelDir,
    db_path,
)
from flood_adapt.object_model.io import unit_system as us


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )
    northsouth_translation: us.UnitfulLength = us.UnitfulLength(
        value=0.0, units=us.UnitTypesLength.meters
    )


class HurricaneEventModel(EventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    ALLOWED_FORCINGS: ClassVar[dict[ForcingType, List[ForcingSource]]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.TRACK,
        ],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [
            ForcingSource.CSV,
            ForcingSource.SYNTHETIC,
            ForcingSource.CONSTANT,
        ],
    }
    template: Template = Template.Hurricane
    hurricane_translation: TranslationModel = TranslationModel()
    track_name: str


class HurricaneEvent(Event[HurricaneEventModel]):
    _attrs_type = HurricaneEventModel

    def __init__(self, data: dict[str, Any] | HurricaneEventModel) -> None:
        super().__init__(data)
        self.site = Site.load_file(db_path(TopLevelDir.static) / "config" / "site.toml")

    def preprocess(self, output_dir: Path):
        spw_file = self.make_spw_file(output_dir=output_dir, recreate=False)
        for forcing in self.get_forcings():
            if isinstance(forcing, (RainfallTrack, WindTrack)):
                forcing.path = spw_file

    def make_spw_file(
        self,
        output_dir: Path,
        recreate: bool = False,
    ) -> Path:
        """
        Create a spiderweb file from a given TropicalCyclone track and save it to the event's input directory.

        Providing the output_dir argument allows to save the spiderweb file in a different directory.

        Parameters
        ----------
        output_dir : Path
            The directory where the spiderweb file is saved (or copied to if it already exists and recreate is False)
        recreate : bool, optional
            If True, the spiderweb file is recreated even if it already exists, by default False

        Returns
        -------
        Path
            the path to the created spiderweb file
        """
        track_forcings = [
            forcing
            for forcing in self.get_forcings()
            if forcing.source == ForcingSource.TRACK
        ]
        if not track_forcings:
            raise ValueError("Cannot create spw file: no track forcing found")

        track_file = None
        for track_forcing in track_forcings:
            if track_forcing.path is not None:
                track_file = track_forcing.path
                break

        if track_file is None:
            raise ValueError("Cannot create spw file: track forcing path is None")

        spw_file = output_dir / f"{self.attrs.track_name}.spw"
        if spw_file.exists():
            if recreate:
                os.remove(spw_file)
            else:
                return spw_file

        self.logger.info(
            f"Creating spiderweb file for hurricane event `{self.attrs.name}`"
        )

        # Initialize the tropical cyclone
        tc = TropicalCyclone()
        tc.read_track(filename=str(track_file), fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if not math.isclose(
            self.attrs.hurricane_translation.eastwest_translation.value, 0
        ) or not math.isclose(
            self.attrs.hurricane_translation.northsouth_translation.value, 0
        ):
            tc = self.translate_tc_track(tc=tc)

        if self.attrs.forcings.get(ForcingType.RAINFALL):
            self.logger.info(
                f"Including rainfall in spiderweb file of hurricane `{self.attrs.name}`"
            )
            rainfall_forcings = self.attrs.forcings[ForcingType.RAINFALL]
            tc.include_rainfall = any(
                rainfall.source == ForcingSource.TRACK for rainfall in rainfall_forcings
            )

        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

        return spw_file

    def translate_tc_track(self, tc: TropicalCyclone):
        self.logger.info(f"Translating the track of the tropical cyclone `{tc.name}`")
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(self.site.attrs.sfincs.config.csname)
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
