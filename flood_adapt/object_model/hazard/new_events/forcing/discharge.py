from flood_adapt.object_model.hazard.event.forcing.forcing import IForcing
from flood_adapt.object_model.hazard.event.timeseries import SyntheticTimeseriesModel
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge


class IDischarge(IForcing):
    pass


class DischargeConstant(IDischarge):
    discharge: UnitfulDischarge


class DischargeSynthetic(IDischarge):
    timeseries: SyntheticTimeseriesModel


class DischargeFromFile(IDischarge):
    path: str
