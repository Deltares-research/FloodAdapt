from typing import Any, Union
import tomli
import tomli_w

from pathlib import Path
import os

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalHurricaneModel,
    IHistoricalHurricane,
)

class HistoricalHurricane(Event, IHistoricalHurricane):
    attrs = HistoricalHurricaneModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        obj = HistoricalHurricane()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalHurricane.parse_obj(toml)

        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        obj = HistoricalHurricane()
        obj.attrs = HistoricalHurricaneModel.parse_obj(data)
        return obj

    def save(self, filepath: Union[str, os.PathLike]):
        """Saving event toml

        Parameters
        ----------
        file : Path
            path to the location where file will be saved
        """
        with open(filepath, "wb") as f:
            tomli_w.dump(self.attrs.dict(exclude_none=True), f)

