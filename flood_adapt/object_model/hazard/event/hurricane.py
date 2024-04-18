import os
from pathlib import Path
from typing import Any, Union

import hydromt.raster  # noqa: F401
import pyproj
import tomli
from cht_cyclones.tropical_cyclone import TropicalCyclone
from shapely.affinity import translate

from flood_adapt.object_model.interface.events import (
    HurricaneEventModel,
    IEvent,
)
from flood_adapt.object_model.io.unitfulvalue import (
    UnitTypesLength,
)
from flood_adapt.object_model.site import Site


class HurricaneEvent(IEvent):
    """
    Event class that describes a 'historical' hurricane event.
    From the timing, location of the event (site), hurricane track and translation,
    It can create a spiderweb file that describes the track to be used in the model, containing wind speed, direction, pressure and rainfall.
    """

    attrs: HurricaneEventModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]) -> "HurricaneEvent":
        """create HurricaneEvent from toml file"""
        obj = HurricaneEvent()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HurricaneEventModel.model_validate(toml)

    @staticmethod
    def load_dict(data: dict[str, Any]) -> "HurricaneEvent":
        """create HurricaneEvent from object, e.g. when initialized from GUI"""
        obj = HurricaneEvent()
        obj.attrs = HurricaneEventModel.model_validate(data)
        return obj

    def make_spw_file(self, database_path: Path, model_dir: Path, site=Site) -> None:
        """
        Create a spiderweb file from the hurricane track.
        Save it in 'database_path'/'model_dir' as 'hurricane.spw'.
        """
        # Location of tropical cyclone database
        cyc_file = database_path.joinpath(
            "input",
            "events",
            f"{self.attrs.name}",
            f"{self.attrs.offshore.hurricane.track_name}.cyc",
        )
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.offshore.hurricane.hurricane_translation.eastwest_translation.value
            != 0
            or self.attrs.offshore.hurricane.hurricane_translation.northsouth_translation.value
            != 0
        ):
            tc = self.translate_tc_track(tc=tc, site=site)

        # Location of spw file
        filename = "hurricane.spw"
        spw_file = model_dir.joinpath(filename)
        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

    def translate_tc_track(self, tc: TropicalCyclone, site: Site) -> TropicalCyclone:
        """
        Translate the track of the tropical cyclone in the local coordinate system of the site.
        The OffshoreModel variables eastwest_translation and northsouth_translation are used.
        """
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(site.attrs.sfincs.csname)
        tc.track = tc.track.to_crs(crs)

        # Translate the track in the local coordinate system
        tc.track["geometry"] = tc.track["geometry"].apply(
            lambda geom: translate(
                geom,
                xoff=self.attrs.offshore.hurricane.hurricane_translation.eastwest_translation.convert(
                    UnitTypesLength.meters
                ).value,
                yoff=self.attrs.offshore.hurricane.hurricane_translation.northsouth_translation.convert(
                    UnitTypesLength.meters
                ).value,
            )
        )

        # Convert the geodataframe to lat/lon
        tc.track = tc.track.to_crs(epsg=4326)
        return tc
