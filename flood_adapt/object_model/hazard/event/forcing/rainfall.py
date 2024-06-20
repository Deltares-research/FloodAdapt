from flood_adapt.object_model.hazard.event.timeseries import TimeseriesModel
from flood_adapt.object_model.interface.events import IForcing
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class IRainfall(IForcing):
    pass


class RainfallConstant(IRainfall):
    intensity: UnitfulIntensity


class RainfallSynthetic(IRainfall):
    timeseries: TimeseriesModel


class RainfallFromModel(IRainfall):
    path: str


class RainfallFromSPWFile(IRainfall):
    path: str
