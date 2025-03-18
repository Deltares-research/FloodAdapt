from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
from pydantic import BaseModel, model_validator

from flood_adapt.object_model.hazard.interface.models import TimeModel
from flood_adapt.object_model.io import unit_system as us


class TideGaugeSource(str, Enum):
    """The accepted input for the variable source in tide_gauge."""

    file = "file"
    noaa_coops = "noaa_coops"


class TideGaugeModel(BaseModel):
    """The accepted input for the variable tide_gauge in Site.

    The obs_station is used for the download of tide gauge data, to be added to the hazard model as water level boundary condition.
    """

    name: Optional[int | str] = None
    description: Optional[str] = ""
    source: TideGaugeSource
    reference: str
    ID: Optional[int] = None  # Attribute used to download from correct gauge
    file: Optional[Path] = None  # for locally stored data
    lat: Optional[float] = None
    lon: Optional[float] = None
    units: us.UnitTypesLength = (
        us.UnitTypesLength.meters
    )  # units of the water levels in the downloaded file

    @model_validator(mode="after")
    def validate_selection_type(self) -> "TideGaugeModel":
        if self.source == TideGaugeSource.file and self.file is None:
            raise ValueError(
                "If `source` is 'file' a file path relative to the static folder should be provided with the attribute 'file'."
            )
        elif self.source == TideGaugeSource.noaa_coops and self.ID is None:
            raise ValueError(
                "If `source` is 'noaa_coops' the id of the station should be provided with the attribute 'ID'."
            )

        return self


class ITideGauge(ABC):
    attrs: TideGaugeModel

    @abstractmethod
    def __init__(self, attrs: TideGaugeModel): ...

    @abstractmethod
    def get_waterlevels_in_time_frame(
        self,
        time: TimeModel,
        out_path: Optional[Path] = None,
        units: us.UnitTypesLength = us.UnitTypesLength.meters,
    ) -> pd.DataFrame: ...

    @abstractmethod
    def _download_tide_gauge_data(self, time: TimeModel) -> pd.DataFrame | None: ...

    @staticmethod
    @abstractmethod
    def _read_imported_waterlevels(time: TimeModel, path: Path) -> pd.DataFrame: ...
