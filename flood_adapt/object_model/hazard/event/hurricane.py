from pathlib import Path
from typing import List

import pyproj
from cht_cyclones.tropical_cyclone import TropicalCyclone
from pydantic import BaseModel
from shapely.affinity import translate

from flood_adapt.object_model.hazard.interface.events import IEvent, IEventModel
from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    ForcingType,
)
from flood_adapt.object_model.interface.scenarios import IScenario
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitTypesLength


class TranslationModel(BaseModel):
    """BaseModel describing the expected variables and data types for translation parameters of hurricane model."""

    eastwest_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )
    northsouth_translation: UnitfulLength = UnitfulLength(
        value=0.0, units=UnitTypesLength.meters
    )


class HurricaneEventModel(IEventModel):
    """BaseModel describing the expected variables and data types for parameters of HistoricalHurricane that extend the parent class Event."""

    ALLOWED_FORCINGS: dict[ForcingType, List[ForcingSource]] = {
        ForcingType.RAINFALL: [
            ForcingSource.CONSTANT,
            ForcingSource.MODEL,
            ForcingSource.TRACK,
        ],
        ForcingType.WIND: [ForcingSource.TRACK],
        ForcingType.WATERLEVEL: [ForcingSource.MODEL],
        ForcingType.DISCHARGE: [ForcingSource.CONSTANT, ForcingSource.SYNTHETIC],
    }

    hurricane_translation: TranslationModel
    track_name: str


class HurricaneEvent(IEvent):
    MODEL_TYPE = HurricaneEventModel

    attrs: HurricaneEventModel

    def process(self, scenario: IScenario):
        """Prepare HurricaneEvent forcings."""
        return

    def make_spw_file(self, model_dir: Path):
        # Location of tropical cyclone database
        cyc_file = self.database.events.get_database_path().joinpath(
            f"{self.attrs.name}", f"{self.attrs.track_name}.cyc"
        )
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane_translation.northsouth_translation.value != 0
        ):
            tc = self.translate_tc_track(tc=tc)

        if self.attrs.forcings[ForcingType.RAINFALL] is not None:
            tc.include_rainfall = (
                self.attrs.forcings[ForcingType.RAINFALL]._source == ForcingSource.TRACK
            )

        # Location of spw file
        filename = "hurricane.spw"
        spw_file = (
            self.database.events.get_database_path(get_input_path=False)
            / self.attrs.name
            / filename
        )

        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

    def translate_tc_track(self, tc: TropicalCyclone):
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(self.database.site.attrs.sfincs.csname)
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
