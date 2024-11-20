from flood_adapt.object_model.interface.object_model import IObject, IObjectModel
from flood_adapt.object_model.interface.path_builder import ObjectDir


class StrategyModel(IObjectModel):
    measures: list[str] = []


class IStrategy(IObject[StrategyModel]):
    dir_name = ObjectDir.strategy
    display_name = "Strategy"

    attrs: StrategyModel
