from flood_adapt.object_model.hazard.interface.forcing import (
    ForcingSource,
    IWind,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity

__all__ = ["WindConstant", "WindSynthetic", "WindFromModel", "WindFromTrack"]


class WindConstant(IWind):
    _source = ForcingSource.CONSTANT

    speed: UnitfulVelocity
    direction: UnitfulDirection


class WindSynthetic(IWind):
    _source = ForcingSource.SYNTHETIC

    path: str


class WindFromModel(IWind):
    _source = ForcingSource.MODEL

    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'y', 'x']
    path: str


class WindFromTrack(IWind):
    _source = ForcingSource.TRACK

    path: str
