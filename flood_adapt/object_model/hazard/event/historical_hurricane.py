import os
from pathlib import Path
from typing import Any, Union

import tomli
import tomli_w
from cht_cyclones.cyclone_track_database import CycloneTrackDatabase

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalHurricaneModel,
    IHistoricalHurricane,
)


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

    def make_spw_file(self, database_path: Path, model_dir: Path):
        # Location of tropical cyclone database
        tc_netcdf = database_path.joinpath(
            "static", "cyclone_track_database", "IBTrACS.NA.v04r00.nc"
        )
        # Initialize the tropical cyclone database
        tc_database = CycloneTrackDatabase("ibtracs", tc_netcdf)
        # Get the index inside the database based on the track name
        idx = tc_database.filter(name=self.attrs.track_name)
        # Get the track based on the index of the track
        tc = tc_database.get_track(index=idx)
        # Location of spw file
        spw_file = model_dir.joinpath(f"{tc.name}.spw")
        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)
