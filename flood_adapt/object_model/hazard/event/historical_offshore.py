import os
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalOffshoreModel,
)
from flood_adapt.object_model.interface.path_builder import (
    db_path,
)
from flood_adapt.object_model.utils import resolve_filepath, save_file_to_database


class HistoricalOffshore(Event):
    rain_ts: Optional[pd.DataFrame] = None
    wind_ts: Optional[pd.DataFrame] = None

    def __init__(self, data: dict[str, Any]):
        """Initialize function called when object is created through the load_file or load_dict methods."""
        if isinstance(data, HistoricalOffshoreModel):
            self.attrs = data
        else:
            self.attrs = HistoricalOffshoreModel.model_validate(data)

        if self.attrs.rainfall.source == "timeseries":
            path = (
                db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
                / self.attrs.rainfall.timeseries_file
            )
            self.rain_ts = Event.read_csv(path)

        if self.attrs.wind.source == "timeseries":
            path = (
                db_path(object_dir=self.dir_name, obj_name=self.attrs.name)
                / self.attrs.wind.timeseries_file
            )
            self.wind_ts = Event.read_csv(path)

    def save_additional(self, toml_path: Path | str | os.PathLike) -> None:
        if self.attrs.rainfall.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.rainfall.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.rainfall.timeseries_file = path.name

        if self.attrs.wind.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.wind.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.wind.timeseries_file = path.name

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

        if self.attrs.tide.source == "timeseries":
            src_path = resolve_filepath(
                self.dir_name, self.attrs.name, self.attrs.tide.timeseries_file
            )
            path = save_file_to_database(src_path, Path(toml_path).parent)
            self.attrs.tide.timeseries_file = path.name
