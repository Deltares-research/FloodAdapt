from flood_adapt.object_model.interface.events import IForcing
from flood_adapt.object_model.io.unitfulvalue import UnitfulIntensity


class IRainfall(IForcing):
    pass


class RainfallConstant(IRainfall):
    intensity: UnitfulIntensity


class RainfallSynthetic(IRainfall):
    # shape_type: Optional[ShapeType] = None
    # cumulative: Optional[UnitfulLength] = None
    # shape_duration: Optional[float] = None
    # shape_peak_time: Optional[float] = None
    # shape_start_time: Optional[float] = None
    # shape_end_time: Optional[float] = None
    file: str


class RainfallFromModel(IRainfall):
    path: str


class RainfallFromSPWFile(IRainfall):
    path: str
