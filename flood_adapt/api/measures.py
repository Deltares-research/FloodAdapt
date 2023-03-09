from flood_adapt.object_model.direct_impact.measure.elevate import Elevate
from flood_adapt.object_model.interface.measures import IElevate


def add_elevate_measure() -> IElevate:
    return Elevate()


def synthetic_load(model: SyntheticModel) -> ISynthetic:
    obj = Synthetic()
    obj.model = model
    for key, value in obj.model.dict().items():
        setattr(obj, key, value)
    return obj
