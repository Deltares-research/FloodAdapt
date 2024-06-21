from pydantic import BaseModel

from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.hazard.event.timeseries import (
    CSVTimeseriesModel,
    SyntheticTimeseriesModel,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulLength, UnitfulTime


class IWaterlevel(IForcing):
    pass


class SurgeModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    timeseries: SyntheticTimeseriesModel


class TideModel(BaseModel):
    """BaseModel describing the expected variables and data types for harmonic tide parameters of synthetic model."""

    harmonic_amplitude: UnitfulLength
    harmonic_period: UnitfulTime
    harmonic_phase: UnitfulTime


class WaterlevelSynthetic(IWaterlevel):
    surge: SurgeModel
    tide: TideModel


class WaterlevelFromFile(IWaterlevel):
    timeseries: CSVTimeseriesModel


class WaterlevelFromModel(IWaterlevel):
    path: str
