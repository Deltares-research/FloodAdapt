from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.hazard.event.timeseries import SyntheticTimeseriesModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class IRainfall(IForcing):
    pass


class RainfallConstant(IRainfall):
    intensity: UnitfulIntensity


class RainfallSynthetic(IRainfall):
    timeseries: SyntheticTimeseriesModel


class RainfallFromModel(IRainfall):
    path: str


class RainfallFromSPWFile(IRainfall):
    path: str


class RainfallFromTrack(IRainfall):
    path: str
