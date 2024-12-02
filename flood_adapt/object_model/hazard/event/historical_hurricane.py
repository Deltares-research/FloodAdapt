import os
from pathlib import Path
from typing import Any

import pyproj
from cht_cyclones.tropical_cyclone import TropicalCyclone
from shapely.affinity import translate

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalHurricaneModel,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class HistoricalHurricane(Event):
    """HistoricalHurricane class object for storing historical hurricane data in a standardized format for use in flood_adapt.

    Attributes
    ----------
    attrs : HistoricalHurricaneModel
        HistoricalHurricaneModel object

    Methods
    -------
    load_file(filepath)
        Load event toml
    load_dict(data)
        Load event toml
    save(filepath)
        Save event toml
    """

    attrs: HistoricalHurricaneModel

    def __init__(self, data: dict[str, Any]) -> None:
        if isinstance(data, HistoricalHurricaneModel):
            self.attrs = data
        else:
            self.attrs = HistoricalHurricaneModel.model_validate(data)

        # Temporary fix until the Hazard refactor is merged.
        # Dont try to load the timeseries data if the object is the default object since that has fake files.
        if self.attrs.name == "default":
            return

        if self.attrs.rainfall.source == "timeseries":
            # This is a temporary fix until the Hazard refactor is merged.
            if self.attrs.rainfall.timeseries_file:
                path = resolve_filepath(
                    object_dir=self.dir_name,
                    obj_name=self.attrs.name,
                    path=self.attrs.rainfall.timeseries_file,
                )
                self.rain_ts = Event.read_csv(path)

        if self.attrs.wind.source == "timeseries":
            # This is a temporary fix until the Hazard refactor is merged.
            if self.attrs.wind.timeseries_file:
                path = resolve_filepath(
                    object_dir=self.dir_name,
                    obj_name=self.attrs.name,
                    path=self.attrs.wind.timeseries_file,
                )
                self.wind_ts = Event.read_csv(path)

        if self.attrs.tide.source == "timeseries":
            # This is a temporary fix until the Hazard refactor is merged.
            if self.attrs.tide.timeseries_file:
                path = resolve_filepath(
                    object_dir=self.dir_name,
                    obj_name=self.attrs.name,
                    path=self.attrs.tide.timeseries_file,
                )
                self.tide_surge_ts = Event.read_csv(path)

    def save_additional(self, toml_path: Path | str | os.PathLike) -> None:
        # Load the track from the (possibly external) .cyc file
        src_path = resolve_filepath(
            object_dir=self.dir_name,
            obj_name=self.attrs.name,
            path=self.attrs.cyc_file,
        )
        path = save_file_to_database(src_path, Path(toml_path).parent)
        self.attrs.cyc_file = path.name

        if self.attrs.rainfall:
            if self.attrs.rainfall.source == "timeseries":
                src_path = resolve_filepath(
                    self.dir_name, self.attrs.name, self.attrs.rainfall.timeseries_file
                )
                path = save_file_to_database(src_path, Path(toml_path).parent)
                self.attrs.rainfall.timeseries_file = path.name
        if self.attrs.wind:
            if self.attrs.wind.source == "timeseries":
                src_path = resolve_filepath(
                    self.dir_name, self.attrs.name, self.attrs.wind.timeseries_file
                )
                path = save_file_to_database(src_path, Path(toml_path).parent)
                self.attrs.wind.timeseries_file = path.name

        if self.attrs.river:
            for river in self.attrs.river:
                if river.source == "timeseries":
                    if river.timeseries_file is None:
                        raise ValueError(
                            "The timeseries file for the river source is not set."
                        )
                    src_path = resolve_filepath(
                        self.dir_name, self.attrs.name, river.timeseries_file
                    )
                    path = save_file_to_database(src_path, Path(toml_path).parent)
                    river.timeseries_file = path.name

        if self.attrs.tide:
            if self.attrs.tide.source == "timeseries":
                src_path = resolve_filepath(
                    self.dir_name, self.attrs.name, self.attrs.tide.timeseries_file
                )
                path = save_file_to_database(src_path, Path(toml_path).parent)
                self.attrs.tide.timeseries_file = path.name

    def make_spw_file(self, event_path: Path, model_dir: Path):
        # Location of tropical cyclone database
        cyc_file = event_path.joinpath(f"{self.attrs.track_name}.cyc")
        # Initialize the tropical cyclone database
        tc = TropicalCyclone()
        tc.read_track(filename=cyc_file, fmt="ddb_cyc")

        # Alter the track of the tc if necessary
        if (
            self.attrs.hurricane_translation.eastwest_translation.value != 0
            or self.attrs.hurricane_translation.northsouth_translation.value != 0
        ):
            tc = self.translate_tc_track(tc=tc)

        if self.attrs.rainfall.source == "track":
            tc.include_rainfall = True
        else:
            tc.include_rainfall = False

        # Location of spw file
        filename = "hurricane.spw"
        spw_file = model_dir.joinpath(filename)
        # Create spiderweb file from the track
        tc.to_spiderweb(spw_file)

    def write_cyc(self, output_dir: Path, track: TropicalCyclone):
        cyc_file = output_dir / f"{self.attrs.track_name}.cyc"
        if cyc_file.exists():
            os.remove(cyc_file)
        # cht_cyclone function to write TropicalCyclone as .cyc file
        track.write_track(filename=cyc_file, fmt="ddb_cyc")

    def translate_tc_track(self, tc: TropicalCyclone):
        from flood_adapt.dbs_controller import Database

        # First convert geodataframe to the local coordinate system
        crs = pyproj.CRS.from_string(Database().site.attrs.sfincs.csname)
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
