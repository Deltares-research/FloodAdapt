from flood_adapt.dbs_classes.path_builder import ObjectDir
from flood_adapt.object_model.interface.object_model import IObject, IObjectModel


class StrategyModel(IObjectModel):
    measures: list[str] = []


class IStrategy(IObject[StrategyModel]):
    dir_name = ObjectDir.strategy
    attrs: StrategyModel
