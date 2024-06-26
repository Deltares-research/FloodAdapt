from flood_adapt.object_model.hazard.new_events.forcing.forcing import (
    ForcingType,
    IForcing,
)
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity


class IWind(IForcing):
    _type = ForcingType.WIND


class WindConstant(IWind):
    speed: UnitfulVelocity
    direction: UnitfulDirection


class WindTimeSeries(IWind):
    path: str


class WindFromModel(IWind):
    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'y', 'x']
    path: str


class WindFromTrack(IWind):
    path: str
