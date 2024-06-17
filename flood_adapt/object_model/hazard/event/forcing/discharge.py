from flood_adapt.object_model.interface.events import IForcing
from flood_adapt.object_model.io.unitfulvalue import UnitfulDischarge


class IDischarge(IForcing):
    pass


class DischargeConstant(IDischarge):
    discharge: UnitfulDischarge


class DischargeSynthetic(IDischarge):
    # shape_type: Optional[ShapeType] = None
    # cumulative: Optional[UnitfulLength] = None
    # shape_duration: Optional[float] = None
    # shape_peak_time: Optional[float] = None
    # shape_start_time: Optional[float] = None
    # shape_end_time: Optional[float] = None
    file: str
