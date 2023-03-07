from flood_adapt.object_model.interface.measures import IElevate
from flood_adapt.object_model.direct_impact.measure.elevate import Elevate


def add_elevate_measure() -> IElevate:
    return Elevate()