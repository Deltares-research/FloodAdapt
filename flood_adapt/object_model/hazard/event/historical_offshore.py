import os
from datetime import datetime
from pathlib import Path
from typing import Any, Union

import pandas as pd
import tomli
import tomli_w

from flood_adapt.object_model.hazard.event.event import Event
from flood_adapt.object_model.interface.events import (
    HistoricalOffshoreModel,
    IEvent,
)


class HistoricalOffshore(Event, IEvent):
    attrs = HistoricalOffshoreModel

    @staticmethod
    def load_file(filepath: Union[str, os.PathLike]):
        """create Synthetic from toml file"""

        obj = HistoricalOffshore()
        with open(filepath, mode="rb") as fp:
            toml = tomli.load(fp)
        obj.attrs = HistoricalOffshoreModel.parse_obj(toml)

        return obj

    @staticmethod
    def load_dict(data: dict[str, Any]):
        """create Synthetic from object, e.g. when initialized from GUI"""

        obj = HistoricalOffshore()
        obj.attrs = HistoricalOffshoreModel.parse_obj(data)
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