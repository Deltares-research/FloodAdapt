import os
from pathlib import Path
from typing import Any, Union

import pyproj
import tomli
import tomli_w
from cht_cyclones.tropical_cyclone import TropicalCyclone
from shapely.affinity import translate

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalHurricaneModel,
    IHistoricalHurricane,
)
from flood_adapt.object_model.site import Site


class HistoricalHurricane(Event, IHistoricalHurricane):
    """HistoricalHurricane class object for storing historical
    hurricane data in a standardized format for use in flood_adapt

    Attributes
    ----------
    attrs : HistoricalHurricaneModel
        HistoricalHurricaneModel object
    Methods
    -------
    load_file(filepath)
        Loading event toml
    load_dict(data)
        Loading event toml
    save(filepath)
        Saving event toml
    """

    attrs = HistoricalHurricaneModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """Loading event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be loaded from

        Returns
        -------
        HistoricalHurricane
            HistoricalHurricane object
        """

        # load toml file
        obj = HistoricalHurricane()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)

        # load toml into object
        obj.attrs = HistoricalHurricaneModel.parse_obj(toml)

        # return object
        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """Loading event toml

        Parameters
        ----------
        data : dict
            dictionary containing event data

        Returns
        -------
        HistoricalHurricane
            HistoricalHurricane object
        """

        # Initialize object
        obj = HistoricalHurricane()

        # load data into object
        obj.attrs = HistoricalHurricaneModel.parse_obj(data)

        # return object
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """

        # save toml file
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

    def make_spw_file(self, database_path: Path, model_dir: Path, site=Site):
        # Location of tropical cyclone database
        cyc_file = database_path.joinpath(
            "input", "events", f"{self.attrs.name}", f"{self.attrs.track_name}.cyc"
        )
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane_translation.northsouth_translation.value != 0
        ):
            tc = self.translate_tc_track(tc=tc, site=site)

        if self.attrs.rainfall.source == "track":
            tc.include_rainfall = True
        else:
            tc.include_rainfall = False

        # Location of spw file
        filename = "hurricane.spw"
        spw_file = model_dir.joinpath(filename)
        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

    def translate_tc_track(self, tc: TropicalCyclone, site: Site):
        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(site.attrs.sfincs.csname)
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
