from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.io.unitfulvalue import UnitfulDirection, UnitfulVelocity


class IWind(IForcing):
    pass


class WindConstant(IWind):
    speed: UnitfulVelocity
    direction: UnitfulDirection


class WindTimeSeries(IWind):
    path: str = None


class WindFromModel(IWind):
    # Required variables: ['wind_u' (m/s), 'wind_v' (m/s)]
    # Required coordinates: ['time', 'y', 'x']
    path: str
