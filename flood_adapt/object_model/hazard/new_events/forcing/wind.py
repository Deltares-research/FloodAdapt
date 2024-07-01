from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingSource,
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity


class IWind(IForcing):
    _type = ForcingType.WIND


class WindConstant(IWind):
    _source = ForcingSource.CONSTANT

    speed: UnitfulVelocity
    direction: UnitfulDirection


class WindTimeSeries(IWind):
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
