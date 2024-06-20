from flood_adapt.object_model.hazard.event.timeseries import TimeseriesModel
from flood_adapt.object_model.interface.events import IForcing
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge


class IDischarge(IForcing):
    pass


class DischargeConstant(IDischarge):
    discharge: UnitfulDischarge


class DischargeSynthetic(IDischarge):
    timeseries: TimeseriesModel


class DischargeFromFile(IDischarge):
    path: str
